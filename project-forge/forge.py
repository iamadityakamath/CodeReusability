#!/usr/bin/env python3
"""Project Forge scaffold engine.

Usage:
  python forge.py <template_key> <project_name>
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def load_registry(registry_path: Path) -> dict[str, str]:
    try:
        return json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(f"Registry not found: {registry_path}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid registry JSON: {exc}")


def is_probably_text_file(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:2048]
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    return True


def replace_placeholders(root: Path, replacements: dict[str, str]) -> None:
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if not is_probably_text_file(file_path):
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        new_content = content
        for key, value in replacements.items():
            new_content = new_content.replace(f"{{{{{key}}}}}", value)

        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        eprint("Usage: python forge.py <template_key> <project_name>")
        return 1

    template_key = sys.argv[1].strip()
    project_name = sys.argv[2].strip()

    if not template_key or not project_name:
        eprint("Error: template_key and project_name must be non-empty.")
        return 1

    root = Path(__file__).resolve().parent
    registry_path = root / "forge.json"

    try:
        registry = load_registry(registry_path)
    except RuntimeError as exc:
        eprint(f"Error: {exc}")
        return 1

    if template_key not in registry:
        available = ", ".join(sorted(registry.keys()))
        eprint(f"Error: unknown template_key '{template_key}'.")
        eprint(f"Available templates: {available}")
        return 1

    template_path = root / registry[template_key]
    if not template_path.exists() or not template_path.is_dir():
        eprint(
            f"Error: template path for '{template_key}' does not exist: {template_path}"
        )
        return 1

    destination = root / "projects" / project_name
    if destination.exists():
        eprint(f"Error: project already exists: {destination}")
        return 1

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_path, destination)

    replacements = {
        "project_name": project_name,
        "author": os.getenv("FORGE_AUTHOR") or os.getenv("USER") or "unknown-author",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    replace_placeholders(destination, replacements)

    print(f"Success: created '{project_name}' from '{template_key}'")
    print(f"Output path: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
