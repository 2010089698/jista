export type EventSummary = {
  id: string;
  name: string;
  date: string; // ISO8601 date string
};

export type StartTimeEntry = {
  competitor: string;
  startTime: string; // HH:mm formatted string
};

export type EventStartTimes = EventSummary & {
  startTimes: StartTimeEntry[];
  fetchedAt: string;
};

export type EventSelectionState = {
  events: EventSummary[];
  selectedEvent: EventStartTimes | null;
  isOffline: boolean;
  isLoading: boolean;
  error?: string;
};
