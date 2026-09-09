from fastapi import APIRouter

from app.api.events import router as events_router
from app.api.ml import router as ml_router
from app.api.weather import router as weather_router

router = APIRouter()
router.include_router(events_router)
router.include_router(weather_router)
router.include_router(ml_router)
