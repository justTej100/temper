from fastapi import APIRouter

router = APIRouter(
    prefix="/events",
    tags=["Events - ML"],
)


@router.get("/{event_slug}/ml")
async def get_event_ml(event_slug: str):
    pass


@router.post("/{event_slug}/ml-jobs")
async def create_ml_job(event_slug: str):
    pass


@router.get("/{event_slug}/ml-jobs/{job_id}")
async def get_ml_job(event_slug: str, job_id: str):
    pass