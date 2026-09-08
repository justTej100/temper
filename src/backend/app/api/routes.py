from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, col, select

from app.config import get_settings
from app.db import get_session
from app.models import (
    City,
    CityModel,
    EdgeSnapshot,
    ForecastJob,
    Market,
    ModelPrediction,
    Observation,
    TempBucket,
    WeatherForecast,
)
from app.schemas import (
    BucketOut,
    EdgeOut,
    IngestForecastPayload,
    IngestMarketDataPayload,
    MarketDetail,
    MarketListItem,
    ModelComparisonOut,
    WeatherForecastPoint,
)

router = APIRouter(prefix="/api")
SessionDep = Annotated[Session, Depends(get_session)]


def _persisted_id(value: int | None) -> int:
    if value is None:
        raise RuntimeError("Persisted entity is missing its primary key")
    return value


def require_admin(
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    settings = get_settings()
    if settings.environment == "production" and not settings.admin_token:
        raise HTTPException(
            503,
            detail={
                "code": "write_actions_disabled",
                "message": "Administrative write actions are disabled",
            },
        )
    if settings.admin_token and x_admin_token != settings.admin_token:
        raise HTTPException(
            401,
            detail={"code": "invalid_admin_token", "message": "Invalid admin token"},
        )


@router.get("/markets/", response_model=list[MarketListItem])
def list_markets(
    session: SessionDep,
    sort: str = Query("volume", pattern="^(volume|edge|date)$"),
    limit: int = Query(50, ge=1, le=200),
):
    markets = session.exec(
        select(Market).where(Market.active == True).order_by(col(Market.volume).desc())
    ).all()

    items: list[MarketListItem] = []
    for m in markets[:limit]:
        city = session.get(City, m.city_id)
        buckets = session.exec(select(TempBucket).where(TempBucket.market_id == m.id)).all()
        top = max(buckets, key=lambda b: b.yes_price) if buckets else None
        edges = session.exec(select(EdgeSnapshot).where(EdgeSnapshot.market_id == m.id)).all()
        max_edge = max((abs(e.edge) for e in edges), default=None)
        best = session.exec(
            select(CityModel)
            .where(
                CityModel.city_id == m.city_id,
                CityModel.temp_type == m.temp_type,
                CityModel.is_best == True,
            )
            .order_by(col(CityModel.trained_at).desc())
        ).first()
        items.append(
            MarketListItem(
                id=_persisted_id(m.id),
                question=m.question,
                city_name=city.name if city else "",
                temp_type=m.temp_type,
                target_date=m.target_date,
                volume=m.volume,
                url=m.url,
                top_bucket_label=top.label if top else None,
                top_bucket_price=top.yes_price if top else None,
                max_edge=max_edge,
                best_model=best.model_type if best else None,
            )
        )

    if sort == "edge":
        items.sort(key=lambda x: x.max_edge or 0, reverse=True)
    elif sort == "date":
        items.sort(key=lambda x: x.target_date)
    else:
        items.sort(key=lambda x: x.volume, reverse=True)
    return items


@router.get("/markets/{market_id}", response_model=MarketDetail)
def get_market(market_id: int, session: SessionDep):
    market = session.get(Market, market_id)
    if not market:
        raise HTTPException(
            404, detail={"code": "market_not_found", "message": "Market not found"}
        )
    city = session.get(City, market.city_id)

    obs = session.exec(
        select(Observation)
        .where(Observation.city_id == market.city_id)
        .order_by(col(Observation.observed_on))
    ).all()
    history = [
        {"date": o.observed_on.isoformat(), "high_c": o.high_c, "low_c": o.low_c}
        for o in obs
    ]

    forecast_rows = session.exec(
        select(WeatherForecast)
        .where(WeatherForecast.city_id == market.city_id)
        .order_by(col(WeatherForecast.forecast_date))
    ).all()
    weather_forecast = [
        WeatherForecastPoint(forecast_date=f.forecast_date, high_c=f.high_c, low_c=f.low_c)
        for f in forecast_rows
    ]

    pred = session.exec(
        select(ModelPrediction)
        .where(ModelPrediction.market_id == market.id)
        .order_by(col(ModelPrediction.generated_at).desc())
    ).first()

    buckets = session.exec(select(TempBucket).where(TempBucket.market_id == market.id)).all()
    edges: dict[int, EdgeSnapshot] = {}
    for edge in session.exec(
        select(EdgeSnapshot)
        .where(EdgeSnapshot.market_id == market.id)
        .order_by(col(EdgeSnapshot.generated_at).desc())
    ).all():
        edges.setdefault(edge.bucket_id, edge)
    bucket_out = []
    for b in buckets:
        bucket_id = _persisted_id(b.id)
        e = edges.get(bucket_id)
        model_p = (pred.bucket_probs or {}).get(b.label) if pred else None
        if model_p is None and e:
            model_p = e.model_prob
        bucket_out.append(
            BucketOut(
                id=bucket_id,
                label=b.label,
                temp_c=b.temp_c,
                yes_price=b.yes_price,
                model_prob=model_p,
                edge=e.edge if e else (float(model_p) - b.yes_price if model_p is not None else None),
            )
        )
    bucket_out.sort(key=lambda b: (b.temp_c is None, b.temp_c or 0))

    models = session.exec(
        select(CityModel)
        .where(CityModel.city_id == market.city_id, CityModel.temp_type == market.temp_type)
        .order_by(col(CityModel.trained_at).desc())
    ).all()
    seen = set()
    comparison = []
    for m in models:
        if m.model_type in seen or not m.is_comparable:
            continue
        seen.add(m.model_type)
        comparison.append(
            ModelComparisonOut(
                model_type=m.model_type,
                mae=m.mae,
                rmse=m.rmse,
                bias=m.bias,
                is_best=m.is_best,
                params=m.params or {},
            )
        )
    comparison.sort(key=lambda x: x.mae if x.mae is not None else 999)

    best = next((c.model_type for c in comparison if c.is_best), None)
    latest_job = session.exec(
        select(ForecastJob)
        .where(ForecastJob.market_id == market.id)
        .order_by(col(ForecastJob.created_at).desc())
    ).first()

    return MarketDetail(
        id=_persisted_id(market.id),
        question=market.question,
        city_id=market.city_id,
        city_name=city.name if city else "",
        icao=city.icao if city else "",
        timezone=city.timezone if city else "",
        data_source=city.data_source if city else "",
        resolution_source=market.resolution_source,
        resolution_station=market.resolution_station,
        supported=market.supported,
        unsupported_reason=market.unsupported_reason,
        temp_type=market.temp_type,
        target_date=market.target_date,
        volume=market.volume,
        url=market.url,
        history=history,
        weather_forecast=weather_forecast,
        forecast_dates=pred.forecast_dates if pred else [],
        forecast_temps=pred.forecast_temps if pred else [],
        point_forecast_c=pred.point_forecast_c if pred else None,
        residual_rmse=pred.residual_rmse if pred else None,
        buckets=bucket_out,
        model_comparison=comparison,
        best_model=best,
        job_status=latest_job.status if latest_job else None,
    )


@router.get("/edges/", response_model=list[EdgeOut])
def list_edges(
    session: SessionDep,
    min_edge: float | None = None,
    limit: int = Query(30, ge=1, le=100),
):
    threshold = min_edge if min_edge is not None else get_settings().edge_threshold
    edges = session.exec(select(EdgeSnapshot).order_by(col(EdgeSnapshot.generated_at).desc())).all()
    seen = set()
    out: list[EdgeOut] = []
    for e in edges:
        key = (e.market_id, e.bucket_id)
        if key in seen:
            continue
        seen.add(key)
        if abs(e.edge) < threshold:
            continue
        market = session.get(Market, e.market_id)
        bucket = session.get(TempBucket, e.bucket_id)
        city = session.get(City, market.city_id) if market else None
        if not market or not bucket:
            continue
        out.append(
            EdgeOut(
                market_id=_persisted_id(market.id),
                question=market.question,
                city_name=city.name if city else "",
                bucket_label=bucket.label,
                model_prob=e.model_prob,
                market_prob=e.market_prob,
                edge=e.edge,
                target_date=market.target_date,
            )
        )
        if len(out) >= limit:
            break
    out.sort(key=lambda x: abs(x.edge), reverse=True)
    return out


def _get_or_create_market(session: Session, city_id: int, item) -> Market:
    market = session.exec(
        select(Market).where(Market.polymarket_event_id == item.polymarket_event_id)
    ).first()
    if not market:
        market = Market(
            city_id=city_id,
            polymarket_event_id=item.polymarket_event_id,
            target_date=item.target_date,
        )
    market.city_id = city_id
    market.polymarket_slug = item.polymarket_slug
    market.question = item.question
    market.temp_type = item.temp_type
    market.target_date = item.target_date
    market.volume = item.volume
    market.url = item.url
    market.active = True
    session.add(market)
    session.flush()
    return market


@router.post("/ingest/market-data", dependencies=[Depends(require_admin)])
def ingest_market_data(payload: IngestMarketDataPayload, session: SessionDep):
    """From `sync`, every few minutes: live prices/volume + the Open-Meteo display forecast."""
    city = session.exec(
        select(City).where(
            City.name == payload.city.name, City.country == payload.city.country
        )
    ).first()
    if not city:
        city = City(
            name=payload.city.name,
            country=payload.city.country,
            latitude=payload.city.latitude,
            longitude=payload.city.longitude,
            timezone=payload.city.timezone,
            icao=payload.city.icao,
        )
    else:
        city.latitude = payload.city.latitude
        city.longitude = payload.city.longitude
        city.timezone = payload.city.timezone
        city.icao = payload.city.icao
    session.add(city)
    session.flush()
    city_id = _persisted_id(city.id)

    for item in payload.markets:
        market = _get_or_create_market(session, city_id, item)
        market_id = _persisted_id(market.id)

        current_bucket_ids: set[int] = set()
        for b in item.buckets:
            query = select(TempBucket).where(TempBucket.market_id == market_id)
            query = query.where(
                TempBucket.token_id == b.token_id if b.token_id else TempBucket.label == b.label
            )
            bucket = session.exec(query).first()
            if not bucket:
                bucket = TempBucket(market_id=market_id, label=b.label)
            bucket.label = b.label
            bucket.temp_c = b.temp_c
            bucket.source_unit = b.source_unit
            bucket.bucket_width_c = b.bucket_width_c
            bucket.is_or_higher = b.is_or_higher
            bucket.is_or_lower = b.is_or_lower
            bucket.token_id = b.token_id
            bucket.yes_price = b.yes_price
            bucket.active = True
            session.add(bucket)
            session.flush()
            current_bucket_ids.add(_persisted_id(bucket.id))

        stale = session.exec(
            select(TempBucket).where(TempBucket.market_id == market_id, TempBucket.active == True)
        ).all()
        for bucket in stale:
            if bucket.id not in current_bucket_ids:
                bucket.active = False
                session.add(bucket)

    for point in payload.weather_forecast:
        row = session.exec(
            select(WeatherForecast).where(
                WeatherForecast.city_id == city_id,
                WeatherForecast.forecast_date == point.forecast_date,
            )
        ).first()
        if not row:
            row = WeatherForecast(city_id=city_id, forecast_date=point.forecast_date)
        row.high_c = point.high_c
        row.low_c = point.low_c
        session.add(row)

    session.commit()
    return {"status": "stored", "city_id": city_id, "markets_updated": len(payload.markets)}


@router.post("/ingest/forecasts", dependencies=[Depends(require_admin)])
def ingest_forecast(payload: IngestForecastPayload, session: SessionDep):
    """From `ml`, daily: a finished, gated forecast. Backend never fits a model itself."""
    market = session.exec(
        select(Market).where(Market.polymarket_event_id == payload.polymarket_event_id)
    ).first()
    if not market:
        raise HTTPException(
            404,
            detail={
                "code": "market_not_found",
                "message": "sync must run before ml can post a forecast for this market",
            },
        )
    market_id = _persisted_id(market.id)

    for prior in session.exec(
        select(CityModel).where(
            CityModel.city_id == market.city_id,
            CityModel.temp_type == market.temp_type,
            CityModel.is_best == True,
        )
    ).all():
        prior.is_best = False
        session.add(prior)

    city_model = CityModel(
        city_id=market.city_id,
        temp_type=market.temp_type,
        model_type=payload.model_type,
        mae=payload.mae,
        rmse=payload.rmse,
        bias=payload.bias,
        metrics={"mae": payload.mae, "rmse": payload.rmse, "bias": payload.bias},
        data_start=payload.data_start,
        data_end=payload.data_end,
        dataset_fingerprint=payload.dataset_fingerprint,
        target_horizon_days=payload.target_horizon_days,
        backtest_folds=payload.backtest_folds,
        calibration_sample_size=payload.calibration_sample_size,
        mlflow_run_id=payload.mlflow_run_id,
        is_best=True,
        is_comparable=True,
    )
    session.add(city_model)
    session.flush()

    prediction = ModelPrediction(
        market_id=market_id,
        city_model_id=city_model.id,
        target_date=market.target_date,
        point_forecast_c=payload.point_forecast_c,
        residual_rmse=payload.residual_rmse,
        calibration_method=payload.calibration_method,
        mlflow_run_id=payload.mlflow_run_id,
        bucket_probs={b.label: b.probability for b in payload.buckets},
        forecast_dates=payload.forecast_dates,
        forecast_temps=payload.forecast_temps,
    )
    session.add(prediction)
    session.flush()

    for result in payload.buckets:
        bucket = session.exec(
            select(TempBucket).where(
                TempBucket.market_id == market_id, TempBucket.label == result.label
            )
        ).first()
        if not bucket:
            continue
        session.add(
            EdgeSnapshot(
                market_id=market_id,
                bucket_id=_persisted_id(bucket.id),
                model_prob=result.probability,
                market_prob=result.market_price,
                edge=result.probability - result.market_price,
            )
        )

    for row in payload.history:
        observation = session.exec(
            select(Observation).where(
                Observation.city_id == market.city_id,
                Observation.observed_on == row.date,
                Observation.source == "ml",
            )
        ).first()
        if not observation:
            observation = Observation(city_id=market.city_id, observed_on=row.date, source="ml")
        observation.high_c = row.high_c
        observation.low_c = row.low_c
        session.add(observation)

    session.commit()
    return {"status": "stored", "city_model_id": city_model.id, "prediction_id": prediction.id}