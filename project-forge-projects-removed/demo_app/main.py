from fastapi import FastAPI

from routers.health import router as health_router

app = FastAPI(title="demo_app")
app.include_router(health_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "project": "demo_app",
        "author": "aditya",
        "created_at": "2026-04-01T02:39:30Z",
        "status": "ok",
    }
