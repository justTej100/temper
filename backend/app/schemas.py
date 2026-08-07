from datetime import date, datetime

from pydantic import BaseModel

from app.models import JobStatus, JobType, TempType


class BucketOut(BaseModel):
    id: int
    label: str
    temp_c: float | None
    yes_price: float
    model_prob: float | None = None
    edge: float | None = None

    model_config = {"from_attributes": True}


class ModelComparisonOut(BaseModel):
    model_type: str
    mae: float | None
    rmse: float | None
    bias: float | None
    is_best: bool
    params: dict = {}


class MarketListItem(BaseModel):
    id: int
    question: str
    city_name: str
    temp_type: TempType
    target_date: date
    volume: float
    url: str
    top_bucket_label: str | None = None
    top_bucket_price: float | None = None
    max_edge: float | None = None
    best_model: str | None = None

    model_config = {"from_attributes": True}


class MarketDetail(BaseModel):
    id: int
    question: str
    city_id: int
    city_name: str
    icao: str
    timezone: str
    data_source: str
    resolution_source: str
    resolution_station: str
    supported: bool
    unsupported_reason: str
    temp_type: TempType
    target_date: date
    volume: float
    url: str
    history: list[dict]
    forecast_dates: list[str]
    forecast_temps: list[float]
    point_forecast_c: float | None
    residual_rmse: float | None
    buckets: list[BucketOut]
    model_comparison: list[ModelComparisonOut]
    best_model: str | None
    job_status: JobStatus | None = None


class JobOut(BaseModel):
    id: int
    market_id: int | None
    job_type: JobType
    status: JobStatus
    error_message: str
    attempts: int
    updated_at: datetime
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class EdgeOut(BaseModel):
    market_id: int
    question: str
    city_name: str
    bucket_label: str
    model_prob: float
    market_prob: float
    edge: float
    target_date: date


class JobCreated(BaseModel):
    job_id: int
    status: JobStatus
    deduplicated: bool = False


# Kept as a schema alias for Phase 1 frontend compatibility.
RetrainResponse = JobCreated
