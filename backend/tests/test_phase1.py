from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import get_session
from app.main import app
from app.models import City, ForecastJob, Market, TempBucket
from app import services
from forecasting.buckets import bucket_probabilities
from forecasting.data_sources import open_meteo
from forecasting.data_sources.polymarket import parse_bucket_label, parse_title
from forecasting import trainer


def test_title_parser_is_high_only_and_rolls_year() -> None:
    parsed = parse_title(
        "Highest temperature in London on January 2?",
        today=date(2026, 12, 31),
    )
    assert parsed == {
        "temp_type": "high",
        "city_raw": "London",
        "target_date": date(2027, 1, 2),
    }
    assert parse_title("Lowest temperature in London on January 2?") is None
    assert parse_title("Highest temperature in London on Feb 29, 2028?")[
        "target_date"
    ] == date(2028, 2, 29)


@pytest.mark.parametrize(
    ("label", "temp_c", "width", "higher", "lower"),
    [
        ("30°C", 30.0, 1.0, False, False),
        ("86°F", 30.0, 5 / 9, False, False),
        ("95°F or higher", 35.0, 5 / 9, True, False),
        ("10°C or lower", 10.0, 1.0, False, True),
    ],
)
def test_bucket_parser_supports_celsius_fahrenheit_and_bounds(
    label, temp_c, width, higher, lower
) -> None:
    parsed = parse_bucket_label(label)
    assert parsed["temp_c"] == pytest.approx(temp_c)
    assert parsed["bucket_width_c"] == pytest.approx(width)
    assert parsed["is_or_higher"] is higher
    assert parsed["is_or_lower"] is lower


def test_empirical_bucket_probabilities_are_normalized_for_fahrenheit() -> None:
    buckets = [
        {
            "label": "68°F or lower",
            "temp_c": 20.0,
            "bucket_width_c": 5 / 9,
            "is_or_lower": True,
            "is_or_higher": False,
        },
        {
            "label": "69°F",
            "temp_c": (69 - 32) * 5 / 9,
            "bucket_width_c": 5 / 9,
            "is_or_lower": False,
            "is_or_higher": False,
        },
        {
            "label": "70°F or higher",
            "temp_c": (70 - 32) * 5 / 9,
            "bucket_width_c": 5 / 9,
            "is_or_lower": False,
            "is_or_higher": True,
        },
    ]
    probabilities = bucket_probabilities(
        20.5, 1.0, buckets, np.linspace(-2, 2, 41)
    )
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert all(0 <= probability <= 1 for probability in probabilities.values())


def test_open_meteo_uses_local_timezone_and_validates_units(monkeypatch) -> None:
    captured = {}

    def fake_json(url, params):
        captured.update(params)
        return {
            "timezone": "America/Chicago",
            "daily_units": {"temperature_2m_max": "°C"},
            "daily": {
                "time": ["2026-08-01", "2026-08-02"],
                "temperature_2m_max": [35.0, 36.0],
            },
        }

    monkeypatch.setattr(open_meteo, "_get_json", fake_json)
    frame = open_meteo.fetch_daily_history(
        32.8, -96.8, "America/Chicago", days=2
    )
    assert captured["timezone"] == "America/Chicago"
    assert captured["temperature_unit"] == "celsius"
    assert frame.high_c.tolist() == [35.0, 36.0]


def test_rolling_evaluation_refits_full_history_and_exact_horizon(monkeypatch) -> None:
    settings = SimpleNamespace(
        max_missing_days=2,
        min_history_days=60,
        max_forecast_horizon_days=30,
        backtest_folds=4,
        mlflow_enabled=False,
    )
    monkeypatch.setattr(trainer, "get_settings", lambda: settings)
    monkeypatch.setattr(trainer, "auto_arima", None)
    monkeypatch.setattr(trainer, "Prophet", None)
    index = pd.date_range("2026-01-01", periods=120, freq="D")
    values = 20 + np.sin(np.arange(120) / 10)
    series = pd.Series(values, index=index)
    target = index[-1].date() + timedelta(days=7)

    output = trainer.train_temperature_models(
        series, 1, "Test City", target, station="TEST"
    )

    assert output.best_model.model_type in {"last_value", "seasonal_naive"}
    assert output.fold_count == 4
    assert output.forecast.index[-1].date() == target
    assert len(output.forecast) == 7
    assert output.best_model.fitted_model is not None
    assert output.calibration_errors


def _event(event_id: str, city: str, slug: str) -> dict:
    station = {
        "name": city,
        "country": "US",
        "lat": 40.0,
        "lon": -75.0,
        "icao": "KAAA",
        "timezone": "America/New_York",
        "resolution_source": "test",
        "resolution_verified": True,
    }
    return {
        "event_id": event_id,
        "slug": slug,
        "question": f"Highest temperature in {city} on August 7?",
        "temp_type": "high",
        "target_date": date(2026, 8, 7),
        "city_raw": city,
        "station": station,
        "volume": 10.0,
        "url": "",
        "resolution_source": "test",
        "resolution_station": "KAAA",
        "supported": True,
        "unsupported_reason": "",
        "buckets": [
            {
                "label": "30°C or higher",
                "temp_c": 30.0,
                "source_unit": "C",
                "bucket_width_c": 1.0,
                "is_or_higher": True,
                "is_or_lower": False,
                "token_id": f"token-{event_id}",
                "yes_price": 0.4,
            }
        ],
    }


def test_sync_upserts_buckets_and_deactivates_absent_markets(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    batches = [
        [_event("1", "Alpha", "alpha"), _event("2", "Beta", "beta")],
        [_event("1", "Alpha", "alpha")],
    ]
    monkeypatch.setattr(services, "fetch_weather_events", lambda: batches.pop(0))

    with Session(engine) as session:
        assert services.sync_markets(session) == 2
        bucket_id = session.exec(select(TempBucket)).first().id
        assert services.sync_markets(session) == 1
        markets = session.exec(select(Market).order_by(Market.polymarket_event_id)).all()
        assert [market.active for market in markets] == [True, False]
        bucket = session.exec(
            select(TempBucket).where(TempBucket.market_id == markets[0].id)
        ).one()
        assert bucket.id == bucket_id
        assert len(session.exec(select(City)).all()) == 2


def test_market_get_is_read_only_and_health_is_live() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        city = City(
            name="Read Only",
            country="US",
            latitude=40,
            longitude=-75,
            icao="KAAA",
            timezone="America/New_York",
            resolution_verified=True,
        )
        session.add(city)
        session.commit()
        session.refresh(city)
        market = Market(
            city_id=city.id,
            polymarket_event_id="readonly",
            polymarket_slug="readonly",
            question="Highest temperature in Read Only on August 7?",
            target_date=date(2026, 8, 7),
            supported=True,
        )
        session.add(market)
        session.commit()
        session.refresh(market)

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        client = TestClient(app)
        assert client.get("/health").json() == {"status": "healthy"}
        response = client.get(f"/api/markets/{market.id}")
        assert response.status_code == 200
        with Session(engine) as session:
            assert session.exec(select(ForecastJob)).all() == []
    finally:
        app.dependency_overrides.clear()
