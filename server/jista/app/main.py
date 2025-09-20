"""FastAPI entrypoint for the Jista backend."""
from fastapi import Depends, FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models import EventsResponse, StartTimeResponse, JOEEventsResponse
from .services.event_service import EventService
from .services.startlist_service import StartlistService
from .services.joe_scraper_service import JOEScraperService

app = FastAPI(title='Jista API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

_service = EventService()
_startlist_service = StartlistService()
_joe_scraper_service = JOEScraperService()


def get_event_service() -> EventService:
    return _service


def get_startlist_service() -> StartlistService:
    return _startlist_service


def get_joe_scraper_service() -> JOEScraperService:
    return _joe_scraper_service


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


class FetchStartlistRequest(BaseModel):
    event_url: str = Field(..., description="Japan-O-Entryの大会ページURL")


@app.post('/events/fetch-startlist', response_model=StartTimeResponse)
def fetch_startlist_from_joe(
    request: FetchStartlistRequest,
    competitor: str | None = Query(None),
    competitor_class: str | None = Query(None),
    event_date: str | None = Query(None),
    startlist_service: StartlistService = Depends(get_startlist_service),
) -> StartTimeResponse:
    """Japan-O-Entryからスタートリストを取得・解析"""
    try:
        result = startlist_service.fetch_event_start_times(
            request.event_url, competitor, competitor_class, event_date
        )
        return StartTimeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")


@app.get('/events/joe-list', response_model=JOEEventsResponse)
def get_joe_events(
    scraper_service: JOEScraperService = Depends(get_joe_scraper_service),
) -> JOEEventsResponse:
    """Japan-O-Entryからイベント一覧を取得"""
    try:
        events = scraper_service.scrape_events()
        return JOEEventsResponse(events=events)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Japan-O-Entry events: {str(exc)}")
