from datetime import UTC, date, datetime
from enum import Enum

from sqlalchemy import JSON, CheckConstraint, Column, Index, UniqueConstraint, text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class TempType(str, Enum):
    high = "high"


class JobStatus(str, Enum):
    queued = "queued"
    fetching = "fetching"
    training = "training"
    evaluating = "evaluating"
    complete = "complete"
    failed = "failed"


class JobType(str, Enum):
    sync = "sync"
    forecast = "forecast"
    scheduled = "scheduled"


class City(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name", "country", name="uq_city_name_country"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    country: str = ""
    latitude: float
    longitude: float
    icao: str = Field(default="", index=True)
    timezone: str
    data_source: str = "open-meteo"
    resolution_source: str = ""
    resolution_verified: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class Market(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("temp_type = 'high'", name="ck_market_high_only"),
    )

    id: int | None = Field(default=None, primary_key=True)
    city_id: int = Field(foreign_key="city.id", index=True)
    polymarket_event_id: str = Field(index=True, unique=True)
    polymarket_slug: str = Field(default="", index=True, unique=True)
    question: str = ""
    temp_type: TempType = TempType.high
    target_date: date = Field(index=True)
    volume: float = 0.0
    active: bool = True
    supported: bool = True
    unsupported_reason: str = ""
    resolution_source: str = ""
    resolution_station: str = ""
    url: str = ""
    last_synced_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class TempBucket(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("market_id", "label", name="uq_bucket_market_label"),
        Index(
            "uq_bucket_market_token",
            "market_id",
            "token_id",
            unique=True,
            postgresql_where=text("token_id <> ''"),
            sqlite_where=text("token_id <> ''"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    market_id: int = Field(foreign_key="market.id", index=True)
    label: str
    temp_c: float | None = None
    source_unit: str = "C"
    bucket_width_c: float = 1.0
    is_or_higher: bool = False
    is_or_lower: bool = False
    token_id: str = ""
    yes_price: float = 0.0
    active: bool = True
    updated_at: datetime = Field(default_factory=utc_now)


class Observation(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "city_id", "observed_on", "source", name="uq_observation_city_day_source"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    city_id: int = Field(foreign_key="city.id", index=True)
    observed_on: date = Field(index=True)
    high_c: float
    source: str = "open-meteo"


class ForecastJob(SQLModel, table=True):
    __table_args__ = (
        Index(
            "uq_active_forecast_job",
            "market_id",
            unique=True,
            postgresql_where=text(
                "job_type = 'forecast' AND status IN "
                "('queued', 'fetching', 'training', 'evaluating')"
            ),
            sqlite_where=text(
                "job_type = 'forecast' AND status IN "
                "('queued', 'fetching', 'training', 'evaluating')"
            ),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    market_id: int | None = Field(default=None, foreign_key="market.id", index=True)
    job_type: JobType = Field(default=JobType.forecast, index=True)
    celery_task_id: str = ""
    status: JobStatus = JobStatus.queued
    error_message: str = ""
    attempts: int = 0
    updated_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class CityModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    city_id: int = Field(foreign_key="city.id", index=True)
    job_id: int | None = Field(default=None, foreign_key="forecastjob.id")
    temp_type: TempType = TempType.high
    model_type: str
    file_path: str = ""
    artifact_uri: str = ""
    params: dict = Field(default_factory=dict, sa_column=Column(JSON))
    metrics: dict = Field(default_factory=dict, sa_column=Column(JSON))
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    data_start: date
    data_end: date
    dataset_fingerprint: str
    code_version: str = "phase1"
    target_horizon_days: int
    backtest_folds: int
    calibration_sample_size: int = 0
    mlflow_run_id: str = ""
    trained_at: datetime = Field(default_factory=utc_now)
    is_best: bool = False
    is_comparable: bool = True


class ModelPrediction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    market_id: int = Field(foreign_key="market.id", index=True)
    city_model_id: int | None = Field(default=None, foreign_key="citymodel.id")
    target_date: date = Field(index=True)
    point_forecast_c: float
    residual_rmse: float = 0.0
    calibration_method: str = "empirical"
    mlflow_run_id: str = ""
    bucket_probs: dict = Field(default_factory=dict, sa_column=Column(JSON))
    forecast_dates: list = Field(default_factory=list, sa_column=Column(JSON))
    forecast_temps: list = Field(default_factory=list, sa_column=Column(JSON))
    generated_at: datetime = Field(default_factory=utc_now)


class EdgeSnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    market_id: int = Field(foreign_key="market.id", index=True)
    bucket_id: int = Field(foreign_key="tempbucket.id", index=True)
    model_prob: float
    market_prob: float
    edge: float
    generated_at: datetime = Field(default_factory=utc_now)
