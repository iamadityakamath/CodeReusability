from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Generator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge_ai import (  # noqa: E402
    assemble,
    build_manifest,
    call_gemini,
    cleanup,
    load_env_files,
    load_registry,
    zip_project,
)

SESSIONS: dict[str, dict[str, Any]] = {}


class ChatRequest(BaseModel):
    message: str
    project_name: str
    session_id: str | None = None


app = FastAPI(title="ReusableAI Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _phase1_prompt() -> str:
    return (
        "1. What application or project do you want to build?\n"
        "2. Any specific libraries, features, or constraints you want included?"
    )


def _is_approval(message: str) -> bool:
    normalized = message.strip().lower()
    approvals = [
        "yes",
        "looks good",
        "approved",
        "approve",
        "go ahead",
        "proceed",
        "generate",
        "ship it",
    ]
    return any(token in normalized for token in approvals)


def _build_output_paths(selections: list[dict]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    primary_key = ""
    if selections:
        primary_key = str(selections[0].get("template_key", ""))

    for selection in selections:
        template_key = str(selection.get("template_key", "")).strip()
        files = selection.get("files", [])
        if not isinstance(files, list):
            continue
        for rel_file in files:
            rel = str(rel_file)
            out = rel
            if out in seen and template_key != primary_key:
                out = f"{template_key}/{rel}"

            suffix = 2
            base = out
            while out in seen:
                p = Path(base)
                out = f"{p.parent.as_posix()}/{p.stem}-{suffix}{p.suffix}" if p.parent.as_posix() != "." else f"{p.stem}-{suffix}{p.suffix}"
                suffix += 1

            seen.add(out)
            paths.append(out)

    return sorted(paths)


def _render_tree(project_name: str, paths: list[str]) -> str:
    root: dict[str, Any] = {}
    for p in paths:
        parts = [x for x in p.split("/") if x]
        node = root
        for idx, part in enumerate(parts):
            if idx == len(parts) - 1:
                node.setdefault("__files__", []).append(part)
            else:
                node = node.setdefault(part, {})

    lines = [f"{project_name}/"]

    def walk(node: dict[str, Any], prefix: str = "") -> None:
        dirs = sorted([k for k in node.keys() if k != "__files__"])
        files = sorted(node.get("__files__", []))
        entries = dirs + files
        for i, name in enumerate(entries):
            last = i == len(entries) - 1
            branch = "└── " if last else "├── "
            lines.append(f"{prefix}{branch}{name}")
            if name in dirs:
                ext = "    " if last else "│   "
                walk(node[name], prefix + ext)

    walk(root)
    return "\n".join(lines)


def _build_preview_message(project_name: str, plan: dict) -> str:
    selections = plan.get("selections", [])
    if not isinstance(selections, list):
        selections = []

    output_paths = _build_output_paths(selections)
    tree = _render_tree(project_name, output_paths)

    keys = [str(s.get("template_key", "")) for s in selections]
    primary = keys[0] if keys else "unknown"
    secondary = ", ".join(keys[1:]) if len(keys) > 1 else "none"

    decisions = (
        "Key decisions:\n"
        f"- Primary template: {primary}\n"
        f"- Secondary templates: {secondary}\n"
        "- Selected the minimal file set needed for your described stack and constraints."
    )

    question = "Does this structure look good, or would you like to make any changes before I generate the ZIP?"

    return f"{tree}\n\n{decisions}\n\n{question}"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    def generate() -> Generator[str, None, None]:
        root = ROOT
        load_env_files(root)

        project_name = req.project_name.strip()
        message = req.message.strip()
        session_id = (req.session_id or project_name).strip()

        if not project_name:
            yield _sse({"type": "error", "message": "project_name is required"})
            return

        session = SESSIONS.get(session_id)
        if session is None:
            SESSIONS[session_id] = {
                "phase": "gather",
                "project_name": project_name,
                "requirements": "",
                "plan": None,
            }
            yield _sse({"type": "phase", "phase": "gather"})
            yield _sse({"type": "assistant", "message": _phase1_prompt()})
            return

        phase = session.get("phase", "gather")

        try:
            if phase == "gather":
                yield _sse({"type": "phase", "phase": "gather"})
                if not message:
                    yield _sse({"type": "assistant", "message": _phase1_prompt()})
                    return

                session["requirements"] = message
                yield _sse({"type": "status", "message": "Building template manifest..."})
                registry = load_registry(root)
                manifest = build_manifest(root, registry)

                yield _sse({"type": "status", "message": "Generating structure preview..."})
                plan = call_gemini(message, project_name, manifest)
                session["plan"] = plan
                session["registry"] = registry
                session["phase"] = "preview"

                yield _sse({"type": "phase", "phase": "preview"})
                preview = _build_preview_message(project_name, plan)
                yield _sse({"type": "assistant", "message": preview})
                return

            if phase == "preview":
                yield _sse({"type": "phase", "phase": "preview"})
                if _is_approval(message):
                    zip_target = root / "projects" / f"{project_name}.zip"
                    if zip_target.exists():
                        yield _sse({"type": "error", "message": f"zip already exists: {zip_target.name}"})
                        return

                    plan = session.get("plan") or {}
                    selections = plan.get("selections", [])
                    if not isinstance(selections, list):
                        raise RuntimeError("Gemini response 'selections' must be a list")

                    author = os.getenv("FORGE_AUTHOR") or os.getenv("USER") or Path.home().name
                    staging_dir = None
                    try:
                        yield _sse({"type": "phase", "phase": "generate"})
                        yield _sse({"type": "status", "message": "Assembling files..."})
                        staging_dir = assemble(root, selections, session["registry"], project_name, author)
                        yield _sse({"type": "status", "message": "Creating zip..."})
                        final_zip = zip_project(root, staging_dir, project_name)
                        session["phase"] = "done"
                        yield _sse({"type": "phase", "phase": "done"})
                        yield _sse(
                            {
                                "type": "success",
                                "message": f"{project_name}.zip created",
                                "zip_path": str(final_zip.resolve()),
                                "download_url": f"/api/download/{project_name}",
                            }
                        )
                    finally:
                        cleanup(staging_dir)
                    return

                # Treat any non-approval as requested changes.
                requirements = str(session.get("requirements", ""))
                revised = (
                    f"Original requirements:\n{requirements}\n\n"
                    f"Requested changes:\n{message}"
                )

                yield _sse({"type": "status", "message": "Applying requested changes..."})
                registry = load_registry(root)
                manifest = build_manifest(root, registry)
                plan = call_gemini(revised, project_name, manifest)

                session["requirements"] = revised
                session["plan"] = plan
                session["registry"] = registry
                session["phase"] = "preview"

                yield _sse({"type": "phase", "phase": "preview"})
                preview = _build_preview_message(project_name, plan)
                yield _sse({"type": "assistant", "message": preview})
                return

            # done or unknown phase
            session["phase"] = "gather"
            session["requirements"] = ""
            session["plan"] = None
            yield _sse({"type": "phase", "phase": "gather"})
            yield _sse({"type": "assistant", "message": _phase1_prompt()})
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/download/{project_name}")
def download(project_name: str):
    zip_path = ROOT / "projects" / f"{project_name}.zip"
    if not zip_path.exists():
        return JSONResponse(status_code=404, content={"error": "Zip not found"})
    return FileResponse(path=str(zip_path), filename=f"{project_name}.zip", media_type="application/zip")
