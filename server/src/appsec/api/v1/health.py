from fastapi import APIRouter
from sqlalchemy import text

from appsec.api.deps import RedisDep, SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(session: SessionDep, redis: RedisDep) -> dict:
    await session.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ready", "database": "ok", "redis": "ok"}
