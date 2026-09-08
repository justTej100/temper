from datetime import date, datetime

from pydantic import BaseModel

from app.models import JobStatus, TempType


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


class WeatherForecastPoint(BaseModel):
    forecast_date: date
    high_c: float | None = None
    low_c: float | None = None


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
    weather_forecast: list[WeatherForecastPoint]
    forecast_dates: list[str]
    forecast_temps: list[float]
    point_forecast_c: float | None
    residual_rmse: float | None
    buckets: list[BucketOut]
    model_comparison: list[ModelComparisonOut]
    best_model: str | None
    job_status: JobStatus | None = None


class EdgeOut(BaseModel):
    market_id: int
    question: str
    city_name: str
    bucket_label: str
    model_prob: float
    market_prob: float
    edge: float
    target_date: date


# --- ingest: from `ml` (daily — one finished, gated forecast) ---

class IngestBucketResult(BaseModel):
    label: str
    probability: float
    market_price: float


class IngestHistoryPoint(BaseModel):
    date: date
    high_c: float | None = None
    low_c: float | None = None


class IngestForecastPayload(BaseModel):
    polymarket_event_id: str
    model_type: str
    mae: float
    rmse: float
    bias: float
    data_start: date
    data_end: date
    dataset_fingerprint: str
    target_horizon_days: int
    backtest_folds: int
    calibration_sample_size: int = 0
    mlflow_run_id: str = ""
    point_forecast_c: float
    residual_rmse: float
    calibration_method: str = "empirical"
    forecast_dates: list[str]
    forecast_temps: list[float]
    buckets: list[IngestBucketResult]
    history: list[IngestHistoryPoint] = []


# --- ingest: from `sync` (frequent — live prices + display forecast) ---

class IngestCity(BaseModel):
    name: str
    country: str = ""
    latitude: float
    longitude: float
    timezone: str
    icao: str = ""


class IngestBucket(BaseModel):
    label: str
    temp_c: float | None = None
    source_unit: str = "C"
    bucket_width_c: float = 1.0
    is_or_higher: bool = False
    is_or_lower: bool = False
    token_id: str = ""
    yes_price: float = 0.0


class IngestMarket(BaseModel):
    polymarket_event_id: str
    polymarket_slug: str = ""
    question: str = ""
    temp_type: TempType
    target_date: date
    volume: float = 0.0
    url: str = ""
    buckets: list[IngestBucket]


class IngestMarketDataPayload(BaseModel):
    city: IngestCity
    markets: list[IngestMarket]
    weather_forecast: list[WeatherForecastPoint] = []