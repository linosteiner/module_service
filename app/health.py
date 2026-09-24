"""Kubernetes probe endpoints.

Liveness says whether the process can still serve at all and deliberately ignores MySQL: a
database outage must not make Kubernetes restart every replica in a loop. Readiness includes
the database, so a pod that lost its connection leaves the Service endpoints instead of
answering requests it cannot serve.
"""

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import DbSession

logger = logging.getLogger(__name__)
health_router = APIRouter(prefix="/health", tags=["health"], include_in_schema=False)


@health_router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "UP"}


@health_router.get("/ready")
def readiness(db: DbSession) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("readiness check failed: %s", exc.__class__.__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "DOWN", "database": "DOWN"},
        )
    return JSONResponse(content={"status": "UP", "database": "UP"})
