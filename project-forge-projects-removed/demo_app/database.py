import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/postgres"
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = asyfrom fastapi import FastAPI

from routers.health import router as health_router

app = FastAPI(title="demo_app")
app.inces
from routers.health impor   
app = FastAPI(title="demo_app")
app.incl'
fapp.include_router(health_router, pref["

@app.get("/")
async def root() -> dict[str, str]my iasync def rome    return {
        "project": "{ i        "prra        "author": "aditya",
     ss        "created_at": "{{creatss        "status": "ok",
    }
