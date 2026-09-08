from fastapi import APIRouter

router = APIRouter(
    prefix="/events",
    tags=["Events - Polymarket"],
)


@router.get("/{event_slug}/polymarket")
async def get_event_polymarket(event_slug: str):
    pass