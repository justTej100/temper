"""Train and compare forecasting models for a single product."""

import logging
import warnings
from dataclasses import dataclass, field

import mlflow
import numpy as np
import pandas as pd
from django.conf import settings
from pmdarima import auto_arima
from prophet import Prophet
from statsmodels.tsa.statespace.sarimax import SARIMAX

from .holidays import build_exogenous_features
from .metrics import mae, mape, rmse
from .storage import save_model, save_prophet_model

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

TRAIN_RATIO = 0.8
FORECAST_HORIZON = 30


@dataclass
class ModelResult:
    model_type: str
    params: dict
    mae: float
    mape: float
    rmse: float
    fitted_model: object = None
    forecast: pd.Series = None
    mlflow_run_id: str = ""
    is_comparable: bool = True


@dataclass
class TrainingOutput:
    results: list[ModelResult] = field(default_factory=list)
    best_model: ModelResult | None = None
    price_history: pd.Series = None
    next_dip_date: str | None = None
    next_dip_price: float | None = None


def _prepare_series(price_points) -> pd.Series:
    """Convert PricePoint queryset to a daily price series."""
    data = [(pp.recorded_at, float(pp.price)) for pp in price_points]
    df = pd.DataFrame(data, columns=["date", "price"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    series = df.groupby("date")["price"].mean().sort_index()
    series = series.asfreq("D", method="ffill")
    return series


def _train_test_split(series: pd.Series):
    split_idx = int(len(series) * TRAIN_RATIO)
    if split_idx < 30:
        split_idx = max(int(len(series) * 0.7), 14)
    train = series.iloc[:split_idx]
    test = series.iloc[split_idx:]
    return train, test


def _log_to_mlflow(result: ModelResult, product_id: int, product_name: str):
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    try:
        with mlflow.start_run(run_name=f"{product_name}_{result.model_type}") as run:
            mlflow.log_param("product_id", product_id)
            mlflow.log_param("product_name", product_name)
            mlflow.log_param("model_type", result.model_type)
            for k, v in result.params.items():
                mlflow.log_param(k, v)
            mlflow.log_metric("mae", result.mae)
            mlflow.log_metric("mape", result.mape)
            mlflow.log_metric("rmse", result.rmse)
            result.mlflow_run_id = run.info.run_id
    except Exception as e:
        logger.warning("MLflow logging failed: %s", e)


def _fit_arima(train: pd.Series, test: pd.Series) -> ModelResult | None:
    try:
        model = auto_arima(
            train,
            seasonal=False,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            max_p=3,
            max_q=3,
            max_d=2,
        )
        forecast = model.predict(n_periods=len(test))
        params = {
            "order": str(model.order),
            "aic": float(model.aic()) if hasattr(model, "aic") else None,
        }
        return ModelResult(
            model_type="arima",
            params=params,
            mae=mae(test.values, forecast),
            mape=mape(test.values, forecast),
            rmse=rmse(test.values, forecast),
            fitted_model=model,
        )
    except Exception as e:
        logger.warning("ARIMA failed: %s", e)
        return None


def _fit_sarima(train: pd.Series, test: pd.Series) -> ModelResult | None:
    try:
        model = auto_arima(
            train,
            seasonal=True,
            m=7,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            max_p=2,
            max_q=2,
            max_P=1,
            max_Q=1,
            max_d=2,
            max_D=1,
        )
        forecast = model.predict(n_periods=len(test))
        params = {
            "order": str(model.order),
            "seasonal_order": str(model.seasonal_order),
            "aic": float(model.aic()) if hasattr(model, "aic") else None,
        }
        return ModelResult(
            model_type="sarima",
            params=params,
            mae=mae(test.values, forecast),
            mape=mape(test.values, forecast),
            rmse=rmse(test.values, forecast),
            fitted_model=model,
        )
    except Exception as e:
        logger.warning("SARIMA failed: %s", e)
        return None


def _fit_arimax(train: pd.Series, test: pd.Series) -> ModelResult | None:
    try:
        exog_train = build_exogenous_features(train.index)
        exog_test = build_exogenous_features(test.index)
        model = auto_arima(
            train,
            exogenous=exog_train,
            seasonal=False,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            max_p=3,
            max_q=3,
            max_d=2,
        )
        forecast = model.predict(n_periods=len(test), exogenous=exog_test)
        params = {
            "order": str(model.order),
            "exog_features": list(exog_train.columns),
            "aic": float(model.aic()) if hasattr(model, "aic") else None,
        }
        return ModelResult(
            model_type="arimax",
            params=params,
            mae=mae(test.values, forecast),
            mape=mape(test.values, forecast),
            rmse=rmse(test.values, forecast),
            fitted_model=model,
        )
    except Exception as e:
        logger.warning("ARIMAX failed: %s", e)
        return None


def _fit_sarimax(train: pd.Series, test: pd.Series) -> ModelResult | None:
    try:
        exog_train = build_exogenous_features(train.index)
        exog_test = build_exogenous_features(test.index)
        model = auto_arima(
            train,
            exogenous=exog_train,
            seasonal=True,
            m=7,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            max_p=2,
            max_q=2,
            max_P=1,
            max_Q=1,
            max_d=2,
            max_D=1,
        )
        forecast = model.predict(n_periods=len(test), exogenous=exog_test)
        params = {
            "order": str(model.order),
            "seasonal_order": str(model.seasonal_order),
            "exog_features": list(exog_train.columns),
            "aic": float(model.aic()) if hasattr(model, "aic") else None,
        }
        return ModelResult(
            model_type="sarimax",
            params=params,
            mae=mae(test.values, forecast),
            mape=mape(test.values, forecast),
            rmse=rmse(test.values, forecast),
            fitted_model=model,
        )
    except Exception as e:
        logger.warning("SARIMAX failed: %s", e)
        return None


def _fit_prophet(train: pd.Series, test: pd.Series) -> ModelResult | None:
    try:
        df = train.reset_index()
        df.columns = ["ds", "y"]
        df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
        )
        model.add_country_holidays(country_name="US")
        model.fit(df)

        future = model.make_future_dataframe(periods=len(test))
        forecast_df = model.predict(future)
        forecast = forecast_df.tail(len(test))["yhat"].values

        params = {
            "changepoint_prior_scale": 0.05,
            "seasonalities": ["yearly", "weekly"],
            "holidays": "US",
        }
        return ModelResult(
            model_type="prophet",
            params=params,
            mae=mae(test.values, forecast),
            mape=mape(test.values, forecast),
            rmse=rmse(test.values, forecast),
            fitted_model=model,
        )
    except Exception as e:
        logger.warning("Prophet failed: %s", e)
        return None


def _fit_garch(train: pd.Series, test: pd.Series) -> ModelResult | None:
    """GARCH models volatility — secondary/complementary experiment."""
    try:
        from arch import arch_model

        returns = train.pct_change().dropna() * 100
        if len(returns) < 30:
            return None
        model = arch_model(returns, vol="Garch", p=1, q=1, rescale=False)
        fitted = model.fit(disp="off")
        forecast = fitted.forecast(horizon=len(test))
        volatility = np.sqrt(forecast.variance.values[-1])

        params = {"p": 1, "q": 1, "vol_model": "Garch"}
        return ModelResult(
            model_type="garch",
            params=params,
            mae=float(np.mean(volatility)),
            mape=0.0,
            rmse=float(np.std(volatility)),
            fitted_model=fitted,
            is_comparable=False,
        )
    except ImportError:
        logger.info("arch package not installed, skipping GARCH")
        return None
    except Exception as e:
        logger.warning("GARCH failed: %s", e)
        return None


def _refit_best_on_full_series(best: ModelResult, series: pd.Series) -> ModelResult:
    """After model selection, refit the winner on all available history."""
    try:
        if best.model_type == "arima":
            model = auto_arima(
                series,
                seasonal=False,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                max_p=3,
                max_q=3,
                max_d=2,
            )
            best.fitted_model = model
            best.params.update({"order": str(model.order), "refit_on_full_history": True})

        elif best.model_type == "sarima":
            model = auto_arima(
                series,
                seasonal=True,
                m=7,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                max_p=2,
                max_q=2,
                max_P=1,
                max_Q=1,
                max_d=2,
                max_D=1,
            )
            best.fitted_model = model
            best.params.update({
                "order": str(model.order),
                "seasonal_order": str(model.seasonal_order),
                "refit_on_full_history": True,
            })

        elif best.model_type == "arimax":
            exog = build_exogenous_features(series.index)
            model = auto_arima(
                series,
                exogenous=exog,
                seasonal=False,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                max_p=3,
                max_q=3,
                max_d=2,
            )
            best.fitted_model = model
            best.params.update({"order": str(model.order), "refit_on_full_history": True})

        elif best.model_type == "sarimax":
            exog = build_exogenous_features(series.index)
            model = auto_arima(
                series,
                exogenous=exog,
                seasonal=True,
                m=7,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                max_p=2,
                max_q=2,
                max_P=1,
                max_Q=1,
                max_d=2,
                max_D=1,
            )
            best.fitted_model = model
            best.params.update({
                "order": str(model.order),
                "seasonal_order": str(model.seasonal_order),
                "refit_on_full_history": True,
            })

        elif best.model_type == "prophet":
            df = series.reset_index()
            df.columns = ["ds", "y"]
            df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.05,
            )
            model.add_country_holidays(country_name="US")
            model.fit(df)
            best.fitted_model = model
            best.params.update({"refit_on_full_history": True})

    except Exception as e:
        logger.warning("Full-history refit failed for %s: %s", best.model_type, e)
    return best

def _generate_forecast(best: ModelResult, series: pd.Series, horizon: int = FORECAST_HORIZON) -> pd.Series:
    """Generate forward forecast from the best model."""
    if best.model_type == "prophet":
        future = best.fitted_model.make_future_dataframe(periods=horizon)
        forecast_df = best.fitted_model.predict(future)
        dates = forecast_df.tail(horizon)["ds"]
        values = forecast_df.tail(horizon)["yhat"].values
        return pd.Series(values, index=pd.DatetimeIndex(dates))

    if best.model_type in ("arima", "sarima"):
        forecast = best.fitted_model.predict(n_periods=horizon)
        last_date = series.index[-1]
        dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D")
        return pd.Series(forecast, index=dates)

    if best.model_type in ("arimax", "sarimax"):
        last_date = series.index[-1]
        dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D")
        exog = build_exogenous_features(dates)
        forecast = best.fitted_model.predict(n_periods=horizon, exogenous=exog)
        return pd.Series(forecast, index=dates)

    return pd.Series(dtype=float)


def _find_next_dip(series: pd.Series, forecast: pd.Series) -> tuple[str | None, float | None]:
    """Find the predicted date of the next price dip."""
    if forecast.empty:
        return None, None

    current_price = float(series.iloc[-1])
    min_idx = forecast.idxmin()
    min_price = float(forecast.min())

    if min_price < current_price * 0.98:
        return min_idx.strftime("%Y-%m-%d"), round(min_price, 2)
    return None, None


def train_all_models(price_points, product_id: int, product_name: str) -> TrainingOutput:
    """Fit all comparable models, log to MLflow, return comparison results."""
    series = _prepare_series(price_points)

    if len(series) < 30:
        raise ValueError(f"Need at least 30 data points, got {len(series)}")

    train, test = _train_test_split(series)
    output = TrainingOutput(price_history=series)

    fitters = [_fit_arima, _fit_sarima, _fit_arimax, _fit_sarimax, _fit_prophet, _fit_garch]

    for fitter in fitters:
        result = fitter(train, test)
        if result is None:
            continue
        _log_to_mlflow(result, product_id, product_name)
        output.results.append(result)

    comparable = [r for r in output.results if r.is_comparable and r.mae is not None]
    if not comparable:
        raise ValueError("All models failed to fit")

    output.best_model = min(comparable, key=lambda r: r.mae)
    output.best_model = _refit_best_on_full_series(output.best_model, series)
    forecast = _generate_forecast(output.best_model, series)
    output.best_model.forecast = forecast
    dip_date, dip_price = _find_next_dip(series, forecast)
    output.next_dip_date = dip_date
    output.next_dip_price = dip_price

    return output


def predict_with_model(product_model, price_points) -> dict:
    """Load a stored model and generate a fresh forecast."""
    from .storage import load_model, load_prophet_model

    series = _prepare_series(price_points)

    if product_model.model_type == "prophet":
        model = load_prophet_model(product_model.file_path)
        future = model.make_future_dataframe(periods=FORECAST_HORIZON)
        forecast_df = model.predict(future)
        forecast = forecast_df.tail(FORECAST_HORIZON)
        dates = forecast["ds"].tolist()
        values = forecast["yhat"].tolist()
    else:
        model = load_model(product_model.file_path)
        if product_model.model_type in ("arimax", "sarimax"):
            last_date = series.index[-1]
            dates_idx = pd.date_range(
                start=last_date + pd.Timedelta(days=1), periods=FORECAST_HORIZON, freq="D"
            )
            exog = build_exogenous_features(dates_idx)
            values = model.predict(n_periods=FORECAST_HORIZON, exogenous=exog).tolist()
            dates = dates_idx.tolist()
        else:
            values = model.predict(n_periods=FORECAST_HORIZON).tolist()
            last_date = series.index[-1]
            dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), periods=FORECAST_HORIZON, freq="D"
            ).tolist()

    forecast_series = pd.Series(values, index=pd.DatetimeIndex(dates))
    dip_date, dip_price = _find_next_dip(series, forecast_series)

    return {
        "forecast_dates": [d.isoformat() for d in dates],
        "forecast_prices": [round(v, 2) for v in values],
        "next_dip_date": dip_date,
        "next_dip_price": dip_price,
        "model_type": product_model.model_type,
    }
