import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { fetchEventStartTimes, fetchEvents } from "../services/api";
import { loadMostRecentEvent, persistEvent } from "../services/storage";
import { EventSelectionState, EventStartTimes } from "../types/events";

type EventSelectionContextValue = EventSelectionState & {
  refreshEvents: () => Promise<void>;
  selectEvent: (eventId: string, competitor?: string) => Promise<void>;
};

const initialState: EventSelectionState = {
  events: [],
  selectedEvent: null,
  isOffline: false,
  isLoading: false,
  error: undefined,
};

const EventSelectionContext = createContext<
  EventSelectionContextValue | undefined
>(undefined);

export const EventProvider: React.FC<React.PropsWithChildren> = ({
  children,
}) => {
  const [state, setState] = useState<EventSelectionState>(initialState);

  useEffect(() => {
    const bootstrap = async () => {
      const cachedEvent = await loadMostRecentEvent();
      if (cachedEvent) {
        setState((prev) => ({
          ...prev,
          selectedEvent: cachedEvent,
          isOffline: true,
        }));
      }
    };

    void bootstrap();
  }, []);

  const refreshEvents = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: undefined }));
    try {
      const events = await fetchEvents();
      setState((prev) => ({
        ...prev,
        events,
        isOffline: false,
        isLoading: false,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : "Failed to load events",
        isOffline: prev.selectedEvent !== null || prev.isOffline,
      }));
    }
  }, []);

  const selectEvent = useCallback(
    async (eventId: string, competitor?: string) => {
      setState((prev) => ({ ...prev, isLoading: true, error: undefined }));
      try {
        const startTimes = await fetchEventStartTimes(eventId, competitor);
        const enriched: EventStartTimes = {
          ...startTimes,
          fetchedAt: startTimes.fetchedAt ?? new Date().toISOString(),
        };
        await persistEvent(enriched);
        setState((prev) => ({
          ...prev,
          selectedEvent: enriched,
          isOffline: false,
          isLoading: false,
        }));
      } catch (error) {
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error:
            error instanceof Error
              ? error.message
              : "Failed to load start times",
        }));
      }
    },
    [],
  );

  const value = useMemo<EventSelectionContextValue>(
    () => ({
      ...state,
      refreshEvents,
      selectEvent,
    }),
    [state, refreshEvents, selectEvent],
  );

  return (
    <EventSelectionContext.Provider value={value}>
      {children}
    </EventSelectionContext.Provider>
  );
};

export const useEventSelection = (): EventSelectionContextValue => {
  const context = useContext(EventSelectionContext);
  if (!context) {
    throw new Error("useEventSelection must be used within an EventProvider");
  }
  return context;
};
