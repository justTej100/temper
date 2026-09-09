import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.config import get_settings
from app.db import engine, init_db

logger = logging.getLogger("temperature_predictor.api")

settings = get_settings()
app = FastAPI(
    title="Temperature Predictor",
    description="Calibrated daily-high temperature forecasts for active Polymarket markets",
    version="1.1.0",
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    # This build ships no Alembic migrations, so tables are created directly
    # from the SQLModel metadata on boot.
    init_db()


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed",
            extra={"request_id": request_id, "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "internal_error",
                    "message": "An internal error occurred",
                    "request_id": request_id,
                }
            },
        )
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        },
    )
    return response


@app.get("/")
def root():
    return {
        "name": "Temperature Predictor API",
        "docs": "/docs",
        "endpoints": {
            "events": "GET /events",
            "event_detail": "GET /events/{event_slug}",
            "event_weather": "GET /events/{event_slug}/weather",
            "event_ml": "GET /events/{event_slug}/ml",
            "create_ml_job": "POST /events/{event_slug}/ml-jobs",
            "ml_job_status": "GET /events/{event_slug}/ml-jobs/{job_id}",
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready():
    failures = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        failures["postgresql"] = str(exc)
    if failures:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "dependencies": failures},
        )
    return {"status": "ready"}
