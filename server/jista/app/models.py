"""Pydantic models for the Jista backend."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StartTimeEntry(BaseModel):
    competitor: str = Field(..., description="Competitor name")
    startTime: str = Field(..., description="Start time in HH:mm format")


class EventSummary(BaseModel):
    id: str = Field(..., description="Unique identifier for the event")
    name: str = Field(..., description="Human readable event name")
    date: str = Field(..., description="Event date (ISO 8601 string)")


class EventStartTimes(EventSummary):
    startTimes: List[StartTimeEntry] = Field(..., description="Start time entries")
    fetchedAt: datetime = Field(default_factory=datetime.utcnow, description="Data retrieval timestamp")

    class Config:
        json_encoders = {datetime: lambda value: value.isoformat()}


class EventsResponse(BaseModel):
    events: List[EventSummary]


class StartTimeResponse(EventStartTimes):
    pass


class EventFilter(BaseModel):
    competitor: Optional[str] = Field(default=None, description="Competitor name filter")


class JOEEvent(BaseModel):
    id: str = Field(..., description="Japan-O-Entry event ID")
    name: str = Field(..., description="Event name")
    date: str = Field(..., description="Event date")
    url: str = Field(..., description="Japan-O-Entry event URL")
    status: str = Field(..., description="Event status (e.g., '受付中', '締切済')")


class JOEEventsResponse(BaseModel):
    events: List[JOEEvent]
