from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(
    title="TempEdge",
    description="Polymarket daily high/low temperature forecasting — model bakeoff vs crowd odds",
    version="1.0.0",
    lifespan=lifespan,
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


@app.get("/")
def root():
    return {
        "name": "TempEdge API",
        "docs": "/docs",
        "endpoints": {
            "markets": "/api/markets/",
            "edges": "/api/edges/",
            "sync": "POST /api/sync/",
            "jobs": "/api/jobs/{id}",
        },
    }
