from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://forecast:forecast@localhost:5433/forecast"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    mlflow_tracking_uri: str = "http://localhost:5000"
    model_storage_path: str = "./model_artifacts"
    model_cache_ttl_hours: int = 24
    edge_threshold: float = 0.08
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    open_meteo_url: str = "https://archive-api.open-meteo.com/v1/archive"
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    metar_api_url: str = "https://aviationweather.gov/api/data/metar"
    history_days: int = 730


@lru_cache
def get_settings() -> Settings:
    return Settings()
