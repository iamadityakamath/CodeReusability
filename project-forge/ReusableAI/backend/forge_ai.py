#!/usr/bin/env python3
"""AI-assisted project forge.

Usage:
  python forge_ai.py "<description>" <project_name>
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_env_files(root: Path) -> None:
    """Autoload .env first, then .env.example for missing keys."""
    for filename in (".env", ".env.example"):
        env_path = root / filename
        if not env_path.exists() or not env_path.is_file():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            os.environ.setdefault(key, _strip_quotes(value.strip()))


def load_registry(root: Path) -> dict[str, str]:
    registry_path = root / "forge.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Registry not found: {registry_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid registry JSON: {exc}") from exc

    templates_root = root / "templates"
    registered_abs_paths = {
        (root / rel_path).resolve() for rel_path in registry.values()
    }

    for candidate in templates_root.rglob("*"):
        if not candidate.is_dir():
            continue
        candidate_abs = candidate.resolve()

        if candidate_abs in registered_abs_paths:
            continue

        # Skip directories inside registered templates.
        if any(_is_relative_to(candidate_abs, r) for r in registered_abs_paths):
            continue

        # Skip container directories that only hold other registered templates.
        if any(_is_relative_to(r, candidate_abs) for r in registered_abs_paths):
            continue

        has_files = any(p.is_file() for p in candidate.rglob("*"))
        if not has_files:
            continue

        rel = candidate.relative_to(root).as_posix()
        key = _derive_template_key(candidate.name)
        if key in registry:
            key = _dedupe_key(key, registry)
        registry[key] = rel

    return registry


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _derive_template_key(name: str) -> str:
    key = name.strip().lower().replace("googel", "google")
    key = re.sub(r"[^a-z0-9]+", "-", key)
    key = re.sub(r"-+", "-", key).strip("-")
    return key or "template"


def _dedupe_key(base: str, existing: dict[str, str]) -> str:
    idx = 2
    candidate = f"{base}-{idx}"
    while candidate in existing:
        idx += 1
        candidate = f"{base}-{idx}"
    return candidate


def build_manifest(root: Path, registry: dict[str, str]) -> dict[str, dict[str, object]]:
    manifest: dict[str, dict[str, object]] = {}
    for key, rel_path in registry.items():
        template_dir = root / rel_path
        files: list[str] = []
        if template_dir.exists() and template_dir.is_dir():
            files = [
                p.relative_to(template_dir).as_posix()
                for p in sorted(template_dir.rglob("*"))
                if p.is_file()
            ]
        manifest[key] = {"path": rel_path, "files": files}
    return manifest


def _extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return text

    depth = 0
    in_string = False
    escape = False
    for idx, ch in enumerate(text[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]

    return text[start:]


def _response_to_text(response: object) -> str:
    text = (getattr(response, "text", "") or "").strip()
    if text:
        return text

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return ""

    parts: list[str] = []
    for cand in candidates:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []):
            part_text = getattr(part, "text", "")
            if part_text:
                parts.append(part_text)
    return "\n".join(parts).strip()


def call_gemini(description: str, project_name: str, manifest: dict[str, dict[str, object]]) -> dict:
    try:
        import google.generativeai as genai  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai package is required. Install with: pip install -r requirements-ai.txt"
        ) from exc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-flash-preview")

    system_prompt = (
        "You are a project scaffolding assistant with access to a library of "
        "code templates. Given a project description, select the minimal set of "
        "template files needed. Return only valid JSON, no markdown, no explanation."
    )

    user_prompt = (
        f"Project name: {project_name}\n"
        f"Description: {description}\n\n"
        "Available templates:\n"
        f"{json.dumps(manifest, indent=2)}\n\n"
        "Return this exact JSON structure:\n"
        "{\n"
        "  \"reasoning\": \"one sentence explaining your choices\",\n"
        "  \"selections\": [\n"
        "    {\n"
        "      \"template_key\": \"fastapi\",\n"
        "      \"files\": [\"main.py\", \"database.py\", \"models.py\", \"routers/health.py\",\n"
        "                \"requirements.txt\", \"Dockerfile\", \"docker-compose.yml\",\n"
        "                \".env.example\", \"README.md\"]\n"
        "    },\n"
        "    {\n"
        "      \"template_key\": \"google-cloud\",\n"
        "      \"files\": [\"services/logging_client.py\", \"services/secret_manager_client.py\"]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Only include files that are genuinely needed for this project\n"
        "- When combining multiple templates, resolve filename conflicts by prefixing files from secondary templates with their template key as a subfolder (e.g. gcp/services/logging_client.py)\n"
        "- Always include README.md, requirements.txt, Dockerfile, docker-compose.yml, .env.example from the primary template\n"
        "- Return ONLY the JSON object, no markdown fences"
    )

    raw_response = ""
    followup_prompt = ""
    parse_error: Exception | None = None

    for attempt in range(1, 4):
        prompt_payload = [system_prompt, user_prompt]
        if followup_prompt:
            prompt_payload.append(followup_prompt)
        try:
            response = model.generate_content(
                prompt_payload,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                    "max_output_tokens": 8192,
                },
            )
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "api key" in msg.lower() and (
                "invalid" in msg.lower() or "unauthorized" in msg.lower()
            ):
                raise RuntimeError(
                    "Gemini authentication failed (invalid API key). "
                    "Set a valid GEMINI_API_KEY in .env or your shell."
                ) from exc
            if (
                "quota" in msg.lower()
                or "billing" in msg.lower()
                or "resource_exhausted" in msg.lower()
            ):
                raise RuntimeError(
                    "Gemini quota/billing error. Check your Google AI Studio or GCP billing/quota settings."
                ) from exc
            raise

        raw_response = _response_to_text(response)
        if raw_response.startswith("```"):
            raw_response = raw_response.strip("`")
            raw_response = raw_response.replace("json", "", 1).strip()

        candidate_json = _extract_first_json_object(raw_response)
        try:
            parsed = json.loads(candidate_json)
            if not isinstance(parsed, dict) or "selections" not in parsed:
                raise RuntimeError("Gemini JSON missing required 'selections' field")
            return parsed
        except Exception as exc:  # noqa: BLE001
            parse_error = exc
            followup_prompt = (
                "Your previous output was invalid or truncated JSON. "
                "Return a complete, valid JSON object only. No markdown, no prose. "
                "Do not omit closing braces or brackets."
            )
            if attempt == 3:
                break
    print("Gemini raw response:")
    print(raw_response)
    raise RuntimeError("Gemini returned invalid JSON") from parse_error


def is_probably_text_file(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:2048]
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    return True


def _replace_placeholders(content: str, project_name: str, author: str, created_at: str) -> str:
    return (
        content.replace("{{project_name}}", project_name)
        .replace("{{author}}", author)
        .replace("{{created_at}}", created_at)
    )


def assemble(
    root: Path,
    selections: list[dict],
    registry: dict[str, str],
    project_name: str,
    author: str,
) -> Path:
    staging_dir = root / "projects" / f".staging_{project_name}"
    staging_dir.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    written_rel_paths: set[str] = set()

    primary_key = ""
    if selections:
        primary_key = str(selections[0].get("template_key", ""))

    for selection in selections:
        template_key = str(selection.get("template_key", "")).strip()
        files = selection.get("files", [])
        if not template_key or not isinstance(files, list):
            continue
        if template_key not in registry:
            eprint(f"Warning: unknown template '{template_key}', skipping")
            continue

        template_root = root / registry[template_key]
        for rel_file in files:
            rel_file_str = str(rel_file)
            src = template_root / rel_file_str
            if not src.exists() or not src.is_file():
                eprint(f"Warning: missing file '{template_key}/{rel_file_str}', skipping")
                continue

            dest_rel = Path(rel_file_str)
            rel_key = dest_rel.as_posix()
            if rel_key in written_rel_paths and template_key != primary_key:
                dest_rel = Path(template_key) / rel_file_str
                rel_key = dest_rel.as_posix()

            # Last-resort dedupe if prefixed path still collides.
            suffix = 2
            while rel_key in written_rel_paths:
                stem = dest_rel.stem
                ext = dest_rel.suffix
                candidate_name = f"{stem}-{suffix}{ext}"
                dest_rel = dest_rel.with_name(candidate_name)
                rel_key = dest_rel.as_posix()
                suffix += 1

            dst = staging_dir / dest_rel
            dst.parent.mkdir(parents=True, exist_ok=True)

            if is_probably_text_file(src):
                try:
                    text = src.read_text(encoding="utf-8")
                    text = _replace_placeholders(text, project_name, author, created_at)
                    dst.write_text(text, encoding="utf-8")
                except UnicodeDecodeError:
                    shutil.copy2(src, dst)
            else:
                shutil.copy2(src, dst)

            written_rel_paths.add(rel_key)

    return staging_dir


def zip_project(root: Path, staging_dir: Path, project_name: str) -> Path:
    output_dir = root / "projects"
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / f"{project_name}.zip"
    suffix = 2
    while zip_path.exists():
                zip_path = output_dir / f"{project_name}-{suffix}.zip"
                suffix += 1

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for item in staging_dir.rglob("*"):
            if not item.is_file():
                continue
            archive_name = Path(project_name) / item.relative_to(staging_dir)
            zf.write(item, arcname=archive_name.as_posix())
    return zip_path


def cleanup(staging_dir: Path | None) -> None:
    if staging_dir and staging_dir.exists() and staging_dir.is_dir():
        shutil.rmtree(staging_dir, ignore_errors=True)


def main() -> int:
    if len(sys.argv) != 3:
        eprint("Usage: python forge_ai.py \"<description>\" <project_name>")
        return 1

    description = sys.argv[1].strip()
    project_name = sys.argv[2].strip()

    if not description or not project_name:
        eprint("Error: description and project_name must be non-empty.")
        return 1

    root = Path(__file__).resolve().parents[2]
    load_env_files(root)

    if not os.getenv("GEMINI_API_KEY"):
        eprint("Error: GEMINI_API_KEY is not set.")
        return 1

    staging_dir: Path | None = None
    try:
        registry = load_registry(root)
        manifest = build_manifest(root, registry)
        plan = call_gemini(description, project_name, manifest)

        selections = plan.get("selections", [])
        if not isinstance(selections, list):
            raise RuntimeError("Gemini response 'selections' must be a list")

        author = os.getenv("FORGE_AUTHOR") or os.getenv("USER") or "unknown-author"
        staging_dir = assemble(root, selections, registry, project_name, author)
        final_zip = zip_project(root, staging_dir, project_name)

        print(f"Reasoning: {plan.get('reasoning', 'No reasoning provided')}")
        print(f"Success: {final_zip.name} created")
        print(f"Output: {final_zip.resolve()}")
        return 0
    except Exception as exc:  # noqa: BLE001
        eprint(f"Error: {exc}")
        return 1
    finally:
        cleanup(staging_dir)


if __name__ == "__main__":
    raise SystemExit(main())
