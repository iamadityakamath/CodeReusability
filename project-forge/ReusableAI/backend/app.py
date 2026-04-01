from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forge_ai import assemble, build_manifest, call_gemini, cleanup, load_env_files, load_registry, zip_project


class ChatRequest(BaseModel):
    message: str
    project_name: str


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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    def generate() -> Generator[str, None, None]:
        root = ROOT
        load_env_files(root)

        if not req.message.strip() or not req.project_name.strip():
            yield _sse({"type": "error", "message": "message and project_name are required"})
            return

        if not (root / "forge_ai.py").exists():
            yield _sse({"type": "error", "message": "forge_ai.py not found at project root"})
            return

        zip_target = root / "projects" / f"{req.project_name}.zip"
        if zip_target.exists():
            yield _sse({"type": "error", "message": f"zip already exists: {zip_target.name}"})
            return

        staging_dir = None
        try:
            yield _sse({"type": "status", "message": "Loading template registry..."})
            registry = load_registry(root)

            yield _sse({"type": "status", "message": "Building manifest..."})
            manifest = build_manifest(root, registry)
            yield _sse(
                {
                    "type": "status",
                    "message": f"Manifest ready with {len(manifest)} templates. Calling Gemini...",
                }
            )

            plan = call_gemini(req.message, req.project_name, manifest)
            reasoning = str(plan.get("reasoning", "No reasoning provided"))
            yield _sse({"type": "reasoning", "message": reasoning})

            selections = plan.get("selections", [])
            if not isinstance(selections, list):
                raise RuntimeError("Gemini response 'selections' must be a list")

            selected_keys = [str(s.get("template_key", "")) for s in selections]
            yield _sse({"type": "status", "message": f"Selected templates: {', '.join(selected_keys)}"})

            author = os.getenv("FORGE_AUTHOR") or os.getenv("USER") or Path.home().name

            yield _sse({"type": "status", "message": "Assembling project files..."})
            staging_dir = assemble(root, selections, registry, req.project_name, author)

            yield _sse({"type": "status", "message": "Creating zip archive..."})
            final_zip = zip_project(root, staging_dir, req.project_name)

            yield _sse(
                {
                    "type": "success",
                    "message": f"{req.project_name}.zip created",
                    "zip_path": str(final_zip.resolve()),
                    "download_url": f"/api/download/{req.project_name}",
                }
            )
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "message": str(exc)})
        finally:
            cleanup(staging_dir)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/download/{project_name}")
def download(project_name: str) -> FileResponse:
    zip_path = ROOT / "projects" / f"{project_name}.zip"
    if not zip_path.exists():
        return FileResponse(path=str(zip_path), status_code=404)
    return FileResponse(path=str(zip_path), filename=f"{project_name}.zip", media_type="application/zip")
