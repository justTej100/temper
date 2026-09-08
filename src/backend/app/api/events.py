from fastapi import APIRouter

router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


@router.get("")
async def get_events():
    pass


@router.get("/{event_slug}")
async def get_event(event_slug: str):
    pass