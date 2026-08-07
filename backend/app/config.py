from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql://forecast:forecast@localhost:5433/forecast"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_enabled: bool = True
    mlflow_experiment: str = "temperature-predictor"
    model_storage_path: str = "./model_artifacts"
    model_cache_ttl_hours: int = 24
    edge_threshold: float = 0.08
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    admin_token: str = ""
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    open_meteo_url: str = "https://archive-api.open-meteo.com/v1/archive"
    geocoding_api_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    history_days: int = 730
    min_history_days: int = 365
    max_missing_days: int = 7
    max_forecast_horizon_days: int = 30
    backtest_folds: int = 5
    http_timeout_seconds: float = 30.0
    http_max_retries: int = 3
    task_soft_time_limit_seconds: int = 840
    task_time_limit_seconds: int = 900
    schedule_minutes: int = 20
    prediction_retention_days: int = 180
    edge_retention_days: int = 180
    job_retention_days: int = 30
    model_retention_days: int = 365


@lru_cache
def get_settings() -> Settings:
    return Settings()
