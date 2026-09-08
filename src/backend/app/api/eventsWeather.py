from fastapi import APIRouter

router = APIRouter(
    prefix="/events",
    tags=["Events - Weather"],
)


@router.get("/{event_slug}/weather")
async def get_event_weather(event_slug: str):
    pass