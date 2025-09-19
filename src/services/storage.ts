import AsyncStorage from "@react-native-async-storage/async-storage";

import { EventStartTimes } from "../types/events";

const SELECTED_EVENTS_KEY = "@jista:selected-events";
const MAX_CACHED_EVENTS = 5;

type StoredEvent = EventStartTimes;

const serialize = (events: StoredEvent[]) => JSON.stringify(events);

const deserialize = (value: string | null): StoredEvent[] => {
  if (!value) {
    return [];
  }
  try {
    const parsed = JSON.parse(value) as StoredEvent[];
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn("Failed to parse stored events", error);
    return [];
  }
};

export const loadStoredEvents = async (): Promise<StoredEvent[]> => {
  const value = await AsyncStorage.getItem(SELECTED_EVENTS_KEY);
  return deserialize(value);
};

export const loadMostRecentEvent = async (): Promise<StoredEvent | null> => {
  const events = await loadStoredEvents();
  if (events.length === 0) {
    return null;
  }
  const [latest] = events.sort((a, b) => (a.fetchedAt < b.fetchedAt ? 1 : -1));
  return latest;
};

export const persistEvent = async (event: StoredEvent): Promise<void> => {
  const events = await loadStoredEvents();
  const filtered = events.filter((existing) => existing.id !== event.id);
  const updated = [event, ...filtered]
    .sort((a, b) => (a.fetchedAt < b.fetchedAt ? 1 : -1))
    .slice(0, MAX_CACHED_EVENTS);
  await AsyncStorage.setItem(SELECTED_EVENTS_KEY, serialize(updated));
};
