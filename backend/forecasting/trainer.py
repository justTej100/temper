"""Bounded, horizon-aware daily-high temperature model selection."""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from app.config import get_settings
from forecasting.metrics import bias, mae, rmse

logger = logging.getLogger(__name__)

try:
    from pmdarima import auto_arima
except ImportError:  # pragma: no cover - optional heavyweight dependency
    auto_arima = None

try:
    from prophet import Prophet
except ImportError:  # pragma: no cover - optional heavyweight dependency
    Prophet = None

try:
    import mlflow
except ImportError:  # pragma: no cover - local operation remains supported
    mlflow = None

RANDOM_SEED = 1729
MIN_CALIBRATION_ERRORS = 20
MAX_CANDIDATE_SECONDS = 240


class LastValueModel:
    def __init__(self, series: pd.Series):
        self.value = float(series.iloc[-1])

    def predict(self, periods: int) -> np.ndarray:
        return np.repeat(self.value, periods)


class SeasonalNaiveModel:
    def __init__(self, series: pd.Series, period: int = 365):
        self.period = min(period, len(series))
        self.tail = np.asarray(series.iloc[-self.period :], dtype=float)

    def predict(self, periods: int) -> np.ndarray:
        return np.resize(self.tail, periods)


@dataclass
class ModelResult:
    model_type: str
    params: dict
    mae: float
    rmse: float
    bias: float
    fitted_model: object = None
    mlflow_run_id: str = ""
    artifact_uri: str = ""
    is_comparable: bool = True
    fold_count: int = 0
    errors: list[float] = field(default_factory=list)


@dataclass
class TrainingOutput:
    results: list[ModelResult] = field(default_factory=list)
    best_model: ModelResult | None = None
    series: pd.Series | None = None
    forecast: pd.Series | None = None
    residual_rmse: float = 1.0
    calibration_errors: list[float] = field(default_factory=list)
    calibration_method: str = "empirical"
    candidate_failures: dict[str, str] = field(default_factory=dict)
    dataset_fingerprint: str = ""
    horizon_days: int = 0
    fold_count: int = 0


def rolling_origins(
    length: int, horizon: int, folds: int, min_train: int
) -> list[tuple[int, int]]:
    if horizon < 1 or length < min_train + horizon:
        return []
    possible = list(range(min_train, length - horizon + 1))
    selected = possible[-max(1, folds) * horizon :: horizon]
    if len(selected) > folds:
        selected = selected[-folds:]
    if not selected:
        selected = [possible[-1]]
    return [(origin, origin + horizon) for origin in selected]


def _prepare_series(series: pd.Series) -> pd.Series:
    settings = get_settings()
    clean = series.dropna().astype(float).sort_index()
    clean.index = pd.DatetimeIndex(clean.index).tz_localize(None).normalize()
    clean = clean.groupby(clean.index).mean()
    if clean.empty or not clean.between(-90.0, 65.0).all():
        raise ValueError("History is empty or contains implausible temperatures")
    full_index = pd.date_range(clean.index.min(), clean.index.max(), freq="D")
    missing = len(full_index) - len(clean)
    if missing > settings.max_missing_days:
        raise ValueError(f"History has {missing} missing days")
    return clean.reindex(full_index).interpolate(method="time", limit_direction="both")


def _dataset_fingerprint(series: pd.Series) -> str:
    payload = "\n".join(
        f"{timestamp.date().isoformat()},{float(value):.5f}"
        for timestamp, value in series.items()
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _fit_baseline(series: pd.Series, name: str) -> object:
    if name == "last_value":
        return LastValueModel(series)
    return SeasonalNaiveModel(series)


def _fit_arima(series: pd.Series, seasonal: bool) -> object:
    if auto_arima is None:
        raise RuntimeError("pmdarima is not installed")
    options = {
        "seasonal": seasonal,
        "stepwise": True,
        "suppress_warnings": True,
        "error_action": "ignore",
        "max_p": 2,
        "max_q": 2,
        "max_d": 1,
        "max_order": 4,
        "random_state": RANDOM_SEED,
    }
    if seasonal:
        options.update({"m": 7, "max_P": 1, "max_Q": 1, "max_D": 1})
    return auto_arima(series, **options)


def _fit_prophet(series: pd.Series) -> object:
    if Prophet is None:
        raise RuntimeError("prophet is not installed")
    frame = series.rename("y").rename_axis("ds").reset_index()
    model = Prophet(
        yearly_seasonality=len(series) >= 730,
        weekly_seasonality=True,
        daily_seasonality=False,
        uncertainty_samples=0,
    )
    model.fit(frame)
    return model


def _predict(model: object, model_type: str, periods: int) -> np.ndarray:
    if model_type in {"last_value", "seasonal_naive"}:
        return np.asarray(model.predict(periods), dtype=float)
    if model_type == "prophet":
        future = model.make_future_dataframe(periods=periods, include_history=False)
        return np.asarray(model.predict(future)["yhat"], dtype=float)
    return np.asarray(model.predict(n_periods=periods), dtype=float)


def _evaluate_candidate(
    name: str,
    fitter: Callable[[pd.Series], object],
    series: pd.Series,
    splits: list[tuple[int, int]],
) -> ModelResult:
    actual_values: list[float] = []
    predicted_values: list[float] = []
    started = time.monotonic()
    for origin, end in splits:
        if time.monotonic() - started > MAX_CANDIDATE_SECONDS:
            raise TimeoutError(f"{name} exceeded its evaluation budget")
        model = fitter(series.iloc[:origin])
        predicted = _predict(model, name, end - origin)
        actual = np.asarray(series.iloc[origin:end], dtype=float)
        if len(predicted) != len(actual) or not np.isfinite(predicted).all():
            raise ValueError(f"{name} returned an invalid forecast")
        actual_values.extend(actual)
        predicted_values.extend(predicted)
    errors = (np.asarray(actual_values) - np.asarray(predicted_values)).tolist()
    return ModelResult(
        model_type=name,
        params={"seed": RANDOM_SEED},
        mae=mae(actual_values, predicted_values),
        rmse=rmse(actual_values, predicted_values),
        bias=bias(actual_values, predicted_values),
        fold_count=len(splits),
        errors=[float(value) for value in errors],
    )


def _log_selected_model(
    result: ModelResult,
    *,
    city_id: int,
    city_name: str,
    station: str,
    series: pd.Series,
    horizon: int,
    fingerprint: str,
    failures: dict[str, str],
) -> None:
    settings = get_settings()
    if not settings.mlflow_enabled or mlflow is None:
        return
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment)
        with mlflow.start_run(
            run_name=f"{city_name}-high-{result.model_type}"
        ) as run:
            mlflow.log_params(
                {
                    "city_id": city_id,
                    "city": city_name,
                    "station": station,
                    "temperature_type": "high",
                    "model_type": result.model_type,
                    "target_horizon_days": horizon,
                    "backtest_folds": result.fold_count,
                    "dataset_fingerprint": fingerprint,
                    **result.params,
                }
            )
            mlflow.log_metrics(
                {
                    "mae": result.mae,
                    "rmse": result.rmse,
                    "bias": result.bias,
                    "calibration_samples": len(result.errors),
                }
            )
            mlflow.log_dict(
                {
                    "data_start": series.index.min().date().isoformat(),
                    "data_end": series.index.max().date().isoformat(),
                    "candidate_failures": failures,
                },
                "provenance.json",
            )
            with tempfile.TemporaryDirectory() as directory:
                model_path = Path(directory) / "model.pkl"
                model_path.write_bytes(pickle.dumps(result.fitted_model))
                mlflow.log_artifact(str(model_path), artifact_path="model")
            result.mlflow_run_id = run.info.run_id
            result.artifact_uri = f"{run.info.artifact_uri}/model/model.pkl"
    except Exception as exc:  # MLflow must not remove the local baseline fallback
        logger.warning("MLflow tracking failed: %s", exc)


def save_model_artifact(model: object, city_id: int, model_type: str) -> str:
    settings = get_settings()
    path = Path(settings.model_storage_path) / f"city_{city_id}"
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / f"{model_type}.pkl"
    file_path.write_bytes(pickle.dumps(model))
    return str(file_path)


def forecast_fitted_model(
    model: object, model_type: str, last_observed_on, target_date
) -> pd.Series:
    start = pd.Timestamp(last_observed_on).normalize()
    horizon = (pd.Timestamp(target_date).normalize() - start).days
    if horizon < 1 or horizon > get_settings().max_forecast_horizon_days:
        raise ValueError("Target date is expired or outside the supported horizon")
    return pd.Series(
        _predict(model, model_type, horizon),
        index=pd.date_range(start + pd.Timedelta(days=1), periods=horizon),
    )


def train_temperature_models(
    series: pd.Series,
    city_id: int,
    city_name: str,
    target_date,
    *,
    station: str = "",
) -> TrainingOutput:
    np.random.seed(RANDOM_SEED)
    settings = get_settings()
    clean = _prepare_series(series)
    if len(clean) < settings.min_history_days:
        raise ValueError(
            f"Need at least {settings.min_history_days} days of history, got {len(clean)}"
        )
    horizon = (pd.Timestamp(target_date).normalize() - clean.index[-1]).days
    if horizon < 1 or horizon > settings.max_forecast_horizon_days:
        raise ValueError(
            f"Target horizon {horizon} is outside 1-{settings.max_forecast_horizon_days} days"
        )
    min_train = min(max(90, horizon * 3), len(clean) - horizon)
    splits = rolling_origins(
        len(clean), horizon, settings.backtest_folds, min_train=min_train
    )
    if not splits:
        raise ValueError("Not enough history for horizon-aware rolling evaluation")

    output = TrainingOutput(
        series=clean,
        horizon_days=horizon,
        fold_count=len(splits),
        dataset_fingerprint=_dataset_fingerprint(clean),
    )
    candidates: list[tuple[str, Callable[[pd.Series], object]]] = [
        ("last_value", lambda values: _fit_baseline(values, "last_value")),
        ("seasonal_naive", lambda values: _fit_baseline(values, "seasonal_naive")),
        ("arima", lambda values: _fit_arima(values, False)),
        ("sarima", lambda values: _fit_arima(values, True)),
        ("prophet", _fit_prophet),
    ]
    for name, fitter in candidates:
        try:
            output.results.append(
                _evaluate_candidate(name, fitter, clean, splits)
            )
        except Exception as exc:
            output.candidate_failures[name] = str(exc)
            logger.warning("Candidate %s failed: %s", name, exc)

    if not output.results:
        raise ValueError("All forecasting candidates failed")
    output.best_model = min(output.results, key=lambda item: (item.mae, item.rmse))
    selected_fitter = dict(candidates)[output.best_model.model_type]
    output.best_model.fitted_model = selected_fitter(clean)
    fitted = output.best_model.fitted_model
    if output.best_model.model_type in {"arima", "sarima"}:
        output.best_model.params.update(
            {
                "order": str(getattr(fitted, "order", "")),
                "seasonal_order": str(getattr(fitted, "seasonal_order", "")),
            }
        )
    elif output.best_model.model_type == "seasonal_naive":
        output.best_model.params["period"] = fitted.period
    elif output.best_model.model_type == "prophet":
        output.best_model.params["yearly_seasonality"] = len(clean) >= 730
    output.forecast = pd.Series(
        _predict(output.best_model.fitted_model, output.best_model.model_type, horizon),
        index=pd.date_range(clean.index[-1] + pd.Timedelta(days=1), periods=horizon),
    )
    output.calibration_errors = output.best_model.errors
    output.calibration_method = (
        "empirical"
        if len(output.calibration_errors) >= MIN_CALIBRATION_ERRORS
        else "gaussian-fallback"
    )
    output.residual_rmse = max(output.best_model.rmse, 0.25)
    _log_selected_model(
        output.best_model,
        city_id=city_id,
        city_name=city_name,
        station=station,
        series=clean,
        horizon=horizon,
        fingerprint=output.dataset_fingerprint,
        failures=output.candidate_failures,
    )
    return output
