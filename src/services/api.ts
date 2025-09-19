import { API_BASE_URL } from "../config";
import { EventStartTimes, EventSummary } from "../types/events";

type EventsResponse = {
  events: EventSummary[];
};

type StartTimesResponse = EventStartTimes;

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "API request failed");
  }
  return response.json() as Promise<T>;
};

export const fetchEvents = async (): Promise<EventSummary[]> => {
  const response = await fetch(`${API_BASE_URL}/events`);
  const data = await handleResponse<EventsResponse>(response);
  return data.events;
};

export const fetchEventStartTimes = async (
  eventId: string,
  competitor?: string,
): Promise<EventStartTimes> => {
  const params = competitor
    ? `?competitor=${encodeURIComponent(competitor)}`
    : "";
  const response = await fetch(
    `${API_BASE_URL}/events/${eventId}/start-times${params}`,
  );
  return handleResponse<StartTimesResponse>(response);
};
