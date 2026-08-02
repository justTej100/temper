"""Train ARIMA-family + Prophet on daily high/low temperature series."""

from __future__ import annotations

import logging
import pickle
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from pmdarima import auto_arima
from prophet import Prophet

from app.config import get_settings
from forecasting.metrics import mae, mape, rmse

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

TRAIN_RATIO = 0.8
FORECAST_HORIZON = 14


@dataclass
class ModelResult:
    model_type: str
    params: dict
    mae: float
    mape: float
    rmse: float
    fitted_model: object = None
    mlflow_run_id: str = ""
    is_comparable: bool = True


@dataclass
class TrainingOutput:
    results: list[ModelResult] = field(default_factory=list)
    best_model: ModelResult | None = None
    series: pd.Series | None = None
    forecast: pd.Series | None = None
    residual_rmse: float = 1.0


def _split(series: pd.Series):
    split_idx = int(len(series) * TRAIN_RATIO)
    split_idx = max(split_idx, min(30, len(series) - 7))
    return series.iloc[:split_idx], series.iloc[split_idx:]


def _log_mlflow(result: ModelResult, city_name: str, temp_type: str):
    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    try:
        with mlflow.start_run(run_name=f"{city_name}_{temp_type}_{result.model_type}") as run:
            mlflow.log_param("city", city_name)
            mlflow.log_param("temp_type", temp_type)
            mlflow.log_param("model_type", result.model_type)
            for k, v in result.params.items():
                mlflow.log_param(k, str(v))
            mlflow.log_metric("mae", result.mae)
            mlflow.log_metric("mape", result.mape)
            mlflow.log_metric("rmse", result.rmse)
            result.mlflow_run_id = run.info.run_id
    except Exception as exc:
        logger.warning("MLflow log failed: %s", exc)


def _fit_arima(train, test, seasonal=False) -> ModelResult | None:
    name = "sarima" if seasonal else "arima"
    try:
        kwargs = dict(
            seasonal=seasonal,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            max_p=3,
            max_q=3,
            max_d=2,
        )
        if seasonal:
            kwargs.update(m=7, max_P=1, max_Q=1, max_D=1)
        model = auto_arima(train, **kwargs)
        forecast = model.predict(n_periods=len(test))
        return ModelResult(
            model_type=name,
            params={"order": str(model.order), "seasonal_order": str(getattr(model, "seasonal_order", None))},
            mae=mae(test.values, forecast),
            mape=mape(test.values, forecast),
            rmse=rmse(test.values, forecast),
            fitted_model=model,
        )
    except Exception as exc:
        logger.warning("%s failed: %s", name, exc)
        return None


def _fit_prophet(train, test) -> ModelResult | None:
    try:
        df = train.reset_index()
        df.columns = ["ds", "y"]
        df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)
        model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        model.fit(df)
        future = model.make_future_dataframe(periods=len(test))
        forecast = model.predict(future).tail(len(test))["yhat"].values
        return ModelResult(
            model_type="prophet",
            params={"seasonalities": ["yearly", "weekly"]},
            mae=mae(test.values, forecast),
            mape=mape(test.values, forecast),
            rmse=rmse(test.values, forecast),
            fitted_model=model,
        )
    except Exception as exc:
        logger.warning("Prophet failed: %s", exc)
        return None


def _calendar_exog(index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({
        "dow": index.dayofweek,
        "month": index.month,
        "is_weekend": (index.dayofweek >= 5).astype(int),
    }, index=index)


def _fit_arimax(train, test, seasonal=False) -> ModelResult | None:
    name = "sarimax" if seasonal else "arimax"
    try:
        exog_train = _calendar_exog(train.index)
        exog_test = _calendar_exog(test.index)
        kwargs = dict(
            exogenous=exog_train,
            seasonal=seasonal,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            max_p=2,
            max_q=2,
            max_d=2,
        )
        if seasonal:
            kwargs.update(m=7, max_P=1, max_Q=1, max_D=1)
        model = auto_arima(train, **kwargs)
        forecast = model.predict(n_periods=len(test), exogenous=exog_test)
        return ModelResult(
            model_type=name,
            params={"order": str(model.order), "exog": ["dow", "month", "is_weekend"]},
            mae=mae(test.values, forecast),
            mape=mape(test.values, forecast),
            rmse=rmse(test.values, forecast),
            fitted_model=model,
        )
    except Exception as exc:
        logger.warning("%s failed: %s", name, exc)
        return None


def _generate_forecast(best: ModelResult, series: pd.Series, horizon: int = FORECAST_HORIZON) -> pd.Series:
    last = series.index[-1]
    dates = pd.date_range(start=last + pd.Timedelta(days=1), periods=horizon, freq="D")
    if best.model_type == "prophet":
        future = best.fitted_model.make_future_dataframe(periods=horizon)
        pred = best.fitted_model.predict(future).tail(horizon)
        return pd.Series(pred["yhat"].values, index=pd.DatetimeIndex(pred["ds"]))
    if best.model_type in ("arimax", "sarimax"):
        exog = _calendar_exog(dates)
        values = best.fitted_model.predict(n_periods=horizon, exogenous=exog)
        return pd.Series(values, index=dates)
    values = best.fitted_model.predict(n_periods=horizon)
    return pd.Series(values, index=dates)


def save_model_artifact(model, city_id: int, model_type: str) -> str:
    settings = get_settings()
    path = Path(settings.model_storage_path) / f"city_{city_id}"
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / f"{model_type}.pkl"
    with open(file_path, "wb") as f:
        pickle.dump(model, f)
    return str(file_path)


def train_temperature_models(
    series: pd.Series,
    city_id: int,
    city_name: str,
    temp_type: str,
) -> TrainingOutput:
    series = series.dropna().astype(float).sort_index()
    series.index = pd.DatetimeIndex(series.index).tz_localize(None).normalize()
    series = series.groupby(series.index).mean().asfreq("D", method="ffill")

    if len(series) < 40:
        raise ValueError(f"Need ≥40 days of history, got {len(series)}")

    train, test = _split(series)
    if len(test) < 3:
        raise ValueError("Test split too small")

    output = TrainingOutput(series=series)
    for fitter in (
        lambda: _fit_arima(train, test, seasonal=False),
        lambda: _fit_arima(train, test, seasonal=True),
        lambda: _fit_arimax(train, test, seasonal=False),
        lambda: _fit_arimax(train, test, seasonal=True),
        lambda: _fit_prophet(train, test),
    ):
        result = fitter()
        if result is None:
            continue
        _log_mlflow(result, city_name, temp_type)
        output.results.append(result)

    comparable = [r for r in output.results if r.is_comparable]
    if not comparable:
        raise ValueError("All models failed")

    output.best_model = min(comparable, key=lambda r: r.mae)
    output.residual_rmse = float(output.best_model.rmse or 1.0)
    output.forecast = _generate_forecast(output.best_model, series)
    return output
