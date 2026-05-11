from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
import structlog

from app.core.config import get_settings, Settings

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/health", tags=["Health"])
async def health_check():
    """Basic liveness check — is the app running?"""
    return {"status": "ok", "service": "tix-backend"}


@router.get("/health/ready", tags=["Health"])
async def readiness_check(settings: Settings = Depends(get_settings)):
    """
    Readiness check — are all dependencies reachable?
    Used by Docker/K8s to decide if traffic should route here.
    """
    results = {}

    # Check PostgreSQL
    try:
        from app.core.database import async_engine
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        results["postgres"] = "ok"
    except Exception as e:
        logger.error("postgres_health_check_failed", error=str(e))
        results["postgres"] = "unreachable"

    # Check Redis
    try:
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        results["redis"] = "ok"
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        results["redis"] = "unreachable"

    all_ok = all(v == "ok" for v in results.values())

    return {
        "status": "ready" if all_ok else "degraded",
        "checks": results,
    }