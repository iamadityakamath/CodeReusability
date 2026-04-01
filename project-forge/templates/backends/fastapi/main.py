from fastapi import FastAPI

from routers.health import router as health_router

app = FastAPI(title="{{project_name}}")
app.include_router(health_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "project": "{{project_name}}",
        "author": "{{author}}",
        "created_at": "{{created_at}}",
        "status": "ok",
    }
