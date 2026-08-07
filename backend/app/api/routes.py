from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, col, select

from app.config import get_settings
from app.db import get_session
from app.models import (
    City,
    CityModel,
    EdgeSnapshot,
    ForecastJob,
    JobStatus,
    JobType,
    Market,
    ModelPrediction,
    Observation,
    TempBucket,
    TempType,
)
from app.schemas import (
    BucketOut,
    EdgeOut,
    JobOut,
    MarketDetail,
    MarketListItem,
    ModelComparisonOut,
    JobCreated,
)
from app.services import create_forecast_job
from app.tasks import run_forecast_pipeline, sync_polymarket_markets

router = APIRouter(prefix="/api")


def require_admin(
    x_admin_token: str | None = Header(default=None),
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


@router.post("/sync/", response_model=JobCreated, dependencies=[Depends(require_admin)])
def trigger_sync(session: Session = Depends(get_session)):
    """Pull latest Polymarket weather markets (also runs on Celery beat)."""
    active = session.exec(
        select(ForecastJob)
        .where(
            ForecastJob.job_type == JobType.sync,
            col(ForecastJob.status).in_(
                [
                    JobStatus.queued,
                    JobStatus.fetching,
                    JobStatus.training,
                    JobStatus.evaluating,
                ]
            ),
        )
        .order_by(col(ForecastJob.created_at).desc())
    ).first()
    if active:
        return JobCreated(
            job_id=active.id, status=active.status, deduplicated=True
        )
    job = ForecastJob(job_type=JobType.sync, status=JobStatus.queued)
    session.add(job)
    session.commit()
    session.refresh(job)
    sync_polymarket_markets.delay(job.id)
    return JobCreated(job_id=job.id, status=job.status)


@router.get("/markets/", response_model=list[MarketListItem])
def list_markets(
    sort: str = Query("volume", pattern="^(volume|edge|date)$"),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    markets = session.exec(
        select(Market)
        .where(
            Market.active == True,  # noqa: E712
            Market.temp_type == TempType.high,
        )
        .order_by(col(Market.volume).desc())
    ).all()

    items: list[MarketListItem] = []
    for m in markets[:limit]:
        city = session.get(City, m.city_id)
        buckets = session.exec(select(TempBucket).where(TempBucket.market_id == m.id)).all()
        top = max(buckets, key=lambda b: b.yes_price) if buckets else None
        edges = session.exec(select(EdgeSnapshot).where(EdgeSnapshot.market_id == m.id)).all()
        max_edge = max((abs(e.edge) for e in edges), default=None)
        best = session.exec(
            select(CityModel).where(
                CityModel.city_id == m.city_id,
                CityModel.temp_type == m.temp_type,
                CityModel.is_best == True,  # noqa: E712
            ).order_by(col(CityModel.trained_at).desc())
        ).first()
        items.append(
            MarketListItem(
                id=m.id,
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
def get_market(market_id: int, session: Session = Depends(get_session)):
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
    history = []
    for o in obs:
        history.append({"date": o.observed_on.isoformat(), "temp_c": float(o.high_c)})

    pred = session.exec(
        select(ModelPrediction)
        .where(ModelPrediction.market_id == market.id)
        .order_by(col(ModelPrediction.generated_at).desc())
    ).first()

    buckets = session.exec(select(TempBucket).where(TempBucket.market_id == market.id)).all()
    edges = {}
    for edge in session.exec(
        select(EdgeSnapshot)
        .where(EdgeSnapshot.market_id == market.id)
        .order_by(col(EdgeSnapshot.generated_at).desc())
    ).all():
        edges.setdefault(edge.bucket_id, edge)
    bucket_out = []
    for b in buckets:
        e = edges.get(b.id)
        model_p = (pred.bucket_probs or {}).get(b.label) if pred else None
        if model_p is None and e:
            model_p = e.model_prob
        bucket_out.append(
            BucketOut(
                id=b.id,
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
        id=market.id,
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
        forecast_dates=pred.forecast_dates if pred else [],
        forecast_temps=pred.forecast_temps if pred else [],
        point_forecast_c=pred.point_forecast_c if pred else None,
        residual_rmse=pred.residual_rmse if pred else None,
        buckets=bucket_out,
        model_comparison=comparison,
        best_model=best,
        job_status=latest_job.status if latest_job else None,
    )


def _queue_forecast(market_id: int, session: Session) -> JobCreated:
    market = session.get(Market, market_id)
    if not market:
        raise HTTPException(
            404, detail={"code": "market_not_found", "message": "Market not found"}
        )
    if not market.supported:
        raise HTTPException(
            422,
            detail={
                "code": "unsupported_market",
                "message": market.unsupported_reason,
            },
        )
    job, created = create_forecast_job(session, market.id)
    if created:
        run_forecast_pipeline.delay(job.id)
    return JobCreated(
        job_id=job.id, status=job.status, deduplicated=not created
    )


@router.post(
    "/markets/{market_id}/forecast",
    response_model=JobCreated,
    dependencies=[Depends(require_admin)],
)
def forecast(market_id: int, session: Session = Depends(get_session)):
    return _queue_forecast(market_id, session)


@router.post(
    "/markets/{market_id}/train",
    response_model=JobCreated,
    dependencies=[Depends(require_admin)],
)
def train(market_id: int, session: Session = Depends(get_session)):
    return _queue_forecast(market_id, session)


@router.post(
    "/markets/{market_id}/retrain",
    response_model=JobCreated,
    dependencies=[Depends(require_admin)],
    deprecated=True,
)
def retrain(market_id: int, session: Session = Depends(get_session)):
    """Compatibility alias; clients should use the explicit train action."""
    return _queue_forecast(market_id, session)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(ForecastJob, job_id)
    if not job:
        raise HTTPException(
            404, detail={"code": "job_not_found", "message": "Job not found"}
        )
    return job


@router.get("/edges/", response_model=list[EdgeOut])
def list_edges(
    min_edge: float | None = None,
    limit: int = Query(30, ge=1, le=100),
    session: Session = Depends(get_session),
):
    threshold = min_edge if min_edge is not None else get_settings().edge_threshold
    edges = session.exec(select(EdgeSnapshot).order_by(col(EdgeSnapshot.generated_at).desc())).all()
    # Deduplicate latest per market+bucket
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
                market_id=market.id,
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
