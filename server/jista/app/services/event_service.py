"""Domain services for working with event data."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models import EventStartTimes, EventSummary, StartTimeEntry

DATA_PATH = Path(__file__).resolve().parent.parent / 'data' / 'sample_events.json'


class EventService:
    """Service responsible for retrieving events and start times."""

    def __init__(self, data_path: Optional[Path] = None) -> None:
        self._data_path = data_path or DATA_PATH
        self._data = self._load_data()

    def _load_data(self) -> Dict[str, List[Dict[str, object]]]:
        with self._data_path.open(encoding='utf-8') as handle:
            return json.load(handle)

    def list_events(self) -> List[EventSummary]:
        events = self._data.get('events', [])
        return [EventSummary(**event) for event in events]

    def get_event_start_times(self, event_id: str, competitor: Optional[str] = None) -> EventStartTimes:
        events = self._data.get('events', [])
        for event in events:
            if event['id'] != event_id:
                continue

            start_times = event.get('startTimes', [])
            if competitor:
                keyword = competitor.strip().lower()
                start_times = [
                    start_time
                    for start_time in start_times
                    if keyword in str(start_time.get('competitor', '')).lower()
                ]

            entries = [StartTimeEntry(**entry) for entry in start_times]
            return EventStartTimes(
                id=event['id'],
                name=event['name'],
                date=event['date'],
                startTimes=entries,
                fetchedAt=datetime.utcnow(),
            )

        raise KeyError(event_id)
