"""Global dip hazard model for buy/wait timing predictions."""

from __future__ import annotations

import math
import pickle
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DIP_THRESHOLD = 0.05
MAX_HORIZON_DAYS = 30
WINDOWS = (3, 7, 14, 30)
MIN_HISTORY_DAYS = 60
MIN_TRAINING_ROWS = 200
MIN_EVENTS = 10
FEATURE_COLUMNS = [
    "horizon_day",
    "current_price",
    "day_of_week",
    "month",
    "pct_above_30d_min",
    "pct_above_90d_min",
    "pct_change_1d",
    "pct_change_7d",
    "rolling_volatility_14d",
    "days_since_30d_low",
]


@dataclass
class DipModelTrainingResult:
    file_path: str
    params: dict
    product_count: int
    observation_count: int
    event_count: int


def _series_from_price_points(price_points) -> pd.Series:
    data = [(pp.recorded_at, float(pp.price)) for pp in price_points]
    if not data:
        return pd.Series(dtype=float)
    df = pd.DataFrame(data, columns=["date", "price"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    series = df.groupby("date")["price"].mean().sort_index()
    return series.asfreq("D", method="ffill")


def _safe_pct(numerator: float, denominator: float) -> float:
    if denominator == 0 or math.isnan(denominator):
        return 0.0
    return float(numerator / denominator)


def _base_features(series: pd.Series, idx: int, horizon_day: int) -> dict:
    current = float(series.iloc[idx])
    current_date = series.index[idx]
    history_30 = series.iloc[max(0, idx - 29) : idx + 1]
    history_90 = series.iloc[max(0, idx - 89) : idx + 1]
    min_30 = float(history_30.min())
    min_90 = float(history_90.min())
    min_30_pos = int(np.argmin(history_30.values))
    days_since_30d_low = len(history_30) - min_30_pos - 1

    if idx >= 1:
        pct_change_1d = _safe_pct(current - float(series.iloc[idx - 1]), float(series.iloc[idx - 1]))
    else:
        pct_change_1d = 0.0
    if idx >= 7:
        pct_change_7d = _safe_pct(current - float(series.iloc[idx - 7]), float(series.iloc[idx - 7]))
    else:
        pct_change_7d = 0.0

    returns_14 = series.pct_change().iloc[max(1, idx - 13) : idx + 1].dropna()
    rolling_volatility = float(returns_14.std()) if len(returns_14) > 1 else 0.0

    return {
        "horizon_day": float(horizon_day),
        "current_price": current,
        "day_of_week": float(current_date.dayofweek),
        "month": float(current_date.month),
        "pct_above_30d_min": _safe_pct(current - min_30, min_30),
        "pct_above_90d_min": _safe_pct(current - min_90, min_90),
        "pct_change_1d": pct_change_1d,
        "pct_change_7d": pct_change_7d,
        "rolling_volatility_14d": rolling_volatility,
        "days_since_30d_low": float(days_since_30d_low),
    }


def _first_dip_day(series: pd.Series, idx: int, threshold: float, max_horizon: int) -> int | None:
    current = float(series.iloc[idx])
    target = current * (1 - threshold)
    future = series.iloc[idx + 1 : idx + max_horizon + 1]
    for day, price in enumerate(future.values, start=1):
        if float(price) <= target:
            return day
    return None


def _training_rows_for_series(series: pd.Series, threshold: float, max_horizon: int) -> tuple[list[dict], int]:
    rows = []
    event_count = 0
    if len(series) < MIN_HISTORY_DAYS + max_horizon:
        return rows, event_count

    for idx in range(30, len(series) - max_horizon):
        first_event_day = _first_dip_day(series, idx, threshold, max_horizon)
        if first_event_day is not None:
            event_count += 1
        risk_days = first_event_day or max_horizon
        for horizon_day in range(1, risk_days + 1):
            row = _base_features(series, idx, horizon_day)
            row["event"] = 1 if first_event_day == horizon_day else 0
            rows.append(row)
    return rows, event_count


def _model_path() -> Path:
    path = Path(settings.MODEL_STORAGE_PATH) / "global" / "dip_hazard.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def train_global_dip_model(force: bool = False) -> DipModelTrainingResult | None:
    """Train one shared discrete-time hazard model across every product."""
    from products.models import GlobalDipModel, Product

    rows = []
    products_used = 0
    event_count = 0
    products = Product.objects.prefetch_related("price_points").all()
    for product in products:
        series = _series_from_price_points(product.price_points.all())
        product_rows, product_events = _training_rows_for_series(series, DIP_THRESHOLD, MAX_HORIZON_DAYS)
        if product_rows:
            rows.extend(product_rows)
            products_used += 1
            event_count += product_events

    if len(rows) < MIN_TRAINING_ROWS or event_count < MIN_EVENTS:
        return None

    df = pd.DataFrame(rows)
    X = df[FEATURE_COLUMNS]
    y = df["event"].astype(int)
    model = Pipeline([
        ("scale", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    model.fit(X, y)

    path = _model_path()
    payload = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "threshold": DIP_THRESHOLD,
        "max_horizon_days": MAX_HORIZON_DAYS,
        "trained_at": timezone.now().isoformat(),
    }
    with open(path, "wb") as f:
        pickle.dump(payload, f)

    GlobalDipModel.objects.filter(is_active=True).update(is_active=False)
    db_model = GlobalDipModel.objects.create(
        file_path=str(path),
        params={
            "model_type": "discrete_time_logistic_hazard",
            "dip_threshold": DIP_THRESHOLD,
            "max_horizon_days": MAX_HORIZON_DAYS,
            "feature_columns": FEATURE_COLUMNS,
        },
        product_count=products_used,
        observation_count=len(rows),
        event_count=event_count,
        is_active=True,
    )
    return DipModelTrainingResult(
        file_path=db_model.file_path,
        params=db_model.params,
        product_count=products_used,
        observation_count=len(rows),
        event_count=event_count,
    )


def _load_active_model():
    from products.models import GlobalDipModel

    db_model = GlobalDipModel.objects.filter(is_active=True).first()
    if not db_model:
        return None, None
    with open(db_model.file_path, "rb") as f:
        payload = pickle.load(f)
    return db_model, payload


def _confidence(prob_14: float, prob_30: float) -> str:
    if prob_14 >= 0.6 or prob_30 >= 0.8:
        return "high"
    if prob_14 >= 0.35 or prob_30 >= 0.55:
        return "medium"
    return "low"


def _recommendation(prob_14: float, prob_30: float, pct_above_30d_min: float) -> str:
    if prob_14 >= 0.45 or (prob_30 >= 0.65 and pct_above_30d_min >= 0.05):
        return "wait"
    if prob_30 <= 0.25 and pct_above_30d_min <= 0.03:
        return "buy"
    return "watch"


def _heuristic_hazards(series: pd.Series) -> tuple[np.ndarray, dict, str]:
    latest_idx = len(series) - 1
    features = _base_features(series, latest_idx, 1)
    base = 0.015
    base += min(features["pct_above_30d_min"], 0.3) * 0.08
    base += min(features["rolling_volatility_14d"], 0.1) * 0.6
    base = min(max(base, 0.005), 0.08)
    hazards = np.array([base * (1 + min(day, 14) / 40) for day in range(1, MAX_HORIZON_DAYS + 1)])
    return hazards, features, "heuristic fallback; not enough shared history for trained global model"


def predict_dip_for_product(product, force_refresh: bool = False):
    """Return and cache dip probability windows for the latest product price."""
    from products.models import DipPrediction

    series = _series_from_price_points(product.price_points.all())
    if len(series) < 30:
        return None

    latest_date = series.index[-1].to_pydatetime()
    latest_price = Decimal(str(round(float(series.iloc[-1]), 2)))
    db_model, payload = _load_active_model()

    cached = DipPrediction.objects.filter(
        product=product,
        global_model=db_model,
        price_as_of=latest_date,
        dip_threshold=DIP_THRESHOLD,
        horizon_days=MAX_HORIZON_DAYS,
    ).first()
    if cached and not force_refresh:
        return cached

    latest_idx = len(series) - 1
    if payload:
        rows = [_base_features(series, latest_idx, day) for day in range(1, MAX_HORIZON_DAYS + 1)]
        X = pd.DataFrame(rows)[payload["feature_columns"]]
        hazards = payload["model"].predict_proba(X)[:, 1]
        hazards = np.clip(hazards, 0.001, 0.35)
        features = rows[0]
        reason = "global hazard model trained across product price histories"
    else:
        hazards, features, reason = _heuristic_hazards(series)

    cumulative = 1 - np.cumprod(1 - hazards)
    probabilities = {f"{window}d": round(float(cumulative[window - 1]), 3) for window in WINDOWS}
    expected_idx = next((idx for idx, prob in enumerate(cumulative, start=1) if prob >= 0.5), None)
    if expected_idx is None:
        expected_idx = int(np.argmax(hazards) + 1)
    expected_date = (series.index[-1] + pd.Timedelta(days=expected_idx)).date()
    expected_price = Decimal(str(round(float(series.iloc[-1]) * (1 - DIP_THRESHOLD), 2)))
    confidence = _confidence(probabilities["14d"], probabilities["30d"])
    recommendation = _recommendation(probabilities["14d"], probabilities["30d"], features["pct_above_30d_min"])

    return DipPrediction.objects.create(
        product=product,
        global_model=db_model,
        price_as_of=latest_date,
        current_price=latest_price,
        dip_threshold=DIP_THRESHOLD,
        horizon_days=MAX_HORIZON_DAYS,
        probabilities=probabilities,
        expected_dip_date=expected_date,
        expected_dip_price=expected_price,
        confidence=confidence,
        recommendation=recommendation,
        reason=reason,
        features={key: round(float(value), 4) for key, value in features.items()},
    )