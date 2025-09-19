"""FastAPI entrypoint for the Jista backend."""
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import EventsResponse, StartTimeResponse
from .services.event_service import EventService

app = FastAPI(title='Jista API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

_service = EventService()


def get_event_service() -> EventService:
    return _service


@app.get('/health')
def health_check() -> dict[str, str]:
    """Simple endpoint for health checks."""
    return {'status': 'ok'}


@app.get('/events', response_model=EventsResponse)
def list_events(service: EventService = Depends(get_event_service)) -> EventsResponse:
    """Return the list of available events."""
    events = service.list_events()
    return EventsResponse(events=events)


@app.get('/events/{event_id}/start-times', response_model=StartTimeResponse)
def get_start_times(
    event_id: str,
    competitor: str | None = None,
    service: EventService = Depends(get_event_service),
) -> StartTimeResponse:
    """Return start times for a specific event."""
    try:
        return service.get_event_start_times(event_id, competitor)
    except KeyError as exc:  # pragma: no cover - simple error mapping
        raise HTTPException(status_code=404, detail='Event not found') from exc
