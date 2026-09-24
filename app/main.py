import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api import module_router, user_module_router
from app.config import get_settings
from app.health import health_router
from app.metrics import PrometheusMiddleware, metrics_endpoint

settings = get_settings()
logging.basicConfig(
    level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Module Service",
    description="Manages modules.",
    version=settings.app_version,
)
app.add_middleware(PrometheusMiddleware)
app.include_router(module_router)
app.include_router(user_module_router)
app.include_router(health_router)
app.add_route("/metrics", metrics_endpoint, include_in_schema=False)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if not isinstance(detail, dict) or "code" not in detail:
        detail = {"code": "HTTP_ERROR", "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=detail, headers=exc.headers)


# A lost database connection is a temporary outage, not a bug: 503 tells the caller (the
# user_mgmt_service's retry and circuit breaker) that trying again later can succeed.
@app.exception_handler(OperationalError)
async def database_unavailable_handler(_: Request, exc: OperationalError) -> JSONResponse:
    logger.error("database unavailable: %s", exc.orig)
    return JSONResponse(
        status_code=503,
        content={"code": "DATABASE_UNAVAILABLE", "message": "The module database is unavailable"},
    )
