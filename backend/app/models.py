from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class TempType(str, Enum):
    high = "high"
    low = "low"


class JobStatus(str, Enum):
    pending = "pending"
    fetching = "fetching"
    training = "training"
    complete = "complete"
    failed = "failed"


class City(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    country: str = ""
    latitude: float
    longitude: float
    icao: str = Field(default="", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Market(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    city_id: int = Field(foreign_key="city.id", index=True)
    polymarket_event_id: str = Field(default="", index=True)
    polymarket_slug: str = Field(default="", index=True, unique=True)
    question: str = ""
    temp_type: TempType = TempType.high
    target_date: date = Field(index=True)
    volume: float = 0.0
    active: bool = True
    url: str = ""
    last_synced_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TempBucket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    market_id: int = Field(foreign_key="market.id", index=True)
    label: str
    temp_c: Optional[float] = None
    is_or_higher: bool = False
    is_or_lower: bool = False
    token_id: str = ""
    yes_price: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Observation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    city_id: int = Field(foreign_key="city.id", index=True)
    observed_on: date = Field(index=True)
    high_c: Optional[float] = None
    low_c: Optional[float] = None
    source: str = "open-meteo"


class ForecastJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    market_id: int = Field(foreign_key="market.id", index=True)
    celery_task_id: str = ""
    status: JobStatus = JobStatus.pending
    error_message: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class CityModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    city_id: int = Field(foreign_key="city.id", index=True)
    job_id: Optional[int] = Field(default=None, foreign_key="forecastjob.id")
    temp_type: TempType = TempType.high
    model_type: str
    file_path: str = ""
    params: dict = Field(default_factory=dict, sa_column=Column(JSON))
    mae: Optional[float] = None
    mape: Optional[float] = None
    rmse: Optional[float] = None
    mlflow_run_id: str = ""
    trained_at: datetime = Field(default_factory=datetime.utcnow)
    is_best: bool = False
    is_comparable: bool = True


class ModelPrediction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    market_id: int = Field(foreign_key="market.id", index=True)
    city_model_id: Optional[int] = Field(default=None, foreign_key="citymodel.id")
    point_forecast_c: float
    residual_rmse: float = 0.0
    bucket_probs: dict = Field(default_factory=dict, sa_column=Column(JSON))
    forecast_dates: list = Field(default_factory=list, sa_column=Column(JSON))
    forecast_temps: list = Field(default_factory=list, sa_column=Column(JSON))
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class EdgeSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    market_id: int = Field(foreign_key="market.id", index=True)
    bucket_id: int = Field(foreign_key="tempbucket.id", index=True)
    model_prob: float
    market_prob: float
    edge: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)
