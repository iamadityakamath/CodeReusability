# ReusableAI Interface

This folder contains a frontend chat UI and a backend API for AI-powered project generation.

## Structure

- backend/: FastAPI server that streams generation logs and creates zip files via forge_ai.py
- frontend/: Static chat interface that consumes the stream and exposes download links

## Run Backend

1. cd backend
2. pip install -r requirements.txt
3. uvicorn app:app --host 0.0.0.0 --port 8008 --reload

Backend endpoints:
- GET /api/health
- POST /api/chat
- GET /api/download/{project_name}

## Run Frontend

Open frontend/index.html in browser.

Set backend base URL in frontend/app.js if needed (default: http://127.0.0.1:8008).

## Notes

- forge_ai.py is imported from project root and used for registry, planning, assembling, and zip creation.
- Output zip files are written to project-forge/projects/.
