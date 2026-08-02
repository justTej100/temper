from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models import JobStatus, TempType


class BucketOut(BaseModel):
    id: int
    label: str
    temp_c: Optional[float]
    yes_price: float
    model_prob: Optional[float] = None
    edge: Optional[float] = None

    model_config = {"from_attributes": True}


class ModelComparisonOut(BaseModel):
    model_type: str
    mae: Optional[float]
    mape: Optional[float]
    rmse: Optional[float]
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
    top_bucket_label: Optional[str] = None
    top_bucket_price: Optional[float] = None
    max_edge: Optional[float] = None
    best_model: Optional[str] = None

    model_config = {"from_attributes": True}


class MarketDetail(BaseModel):
    id: int
    question: str
    city_id: int
    city_name: str
    icao: str
    temp_type: TempType
    target_date: date
    volume: float
    url: str
    history: list[dict]
    forecast_dates: list[str]
    forecast_temps: list[float]
    point_forecast_c: Optional[float]
    residual_rmse: Optional[float]
    buckets: list[BucketOut]
    model_comparison: list[ModelComparisonOut]
    best_model: Optional[str]
    job_status: Optional[JobStatus] = None


class JobOut(BaseModel):
    id: int
    market_id: int
    status: JobStatus
    error_message: str
    created_at: datetime
    completed_at: Optional[datetime]

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


class RetrainResponse(BaseModel):
    job_id: int
    status: str
