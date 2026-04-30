import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const API_BASE_URL = "";
const TRACKING_STATE_KEY = "journaliseTracking";

type TrackingContextValue = {
  isTracking: boolean;
  isTrackingPending: boolean;
  refreshTracking: () => Promise<void>;
  setTrackingEnabled: (enabled: boolean) => Promise<void>;
};

const TrackingContext = createContext<TrackingContextValue | null>(null);

function getToken() {
  const token = localStorage.getItem("accessToken") || localStorage.getItem("token");

  if (!token || token === "undefined" || token === "null") {
    return "";
  }

  return token;
}

function trackingHeaders() {
  const token = getToken();

  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export function TrackingProvider({ children }: { children: ReactNode }) {
  const [isTracking, setIsTracking] = useState(() => {
    return localStorage.getItem(TRACKING_STATE_KEY) === "true";
  });
  const [isTrackingPending, setIsTrackingPending] = useState(false);

  const updateLocalTracking = useCallback((value: boolean) => {
    setIsTracking(value);
    localStorage.setItem(TRACKING_STATE_KEY, String(value));
  }, []);

  const refreshTracking = useCallback(async () => {
    if (!getToken()) {
      updateLocalTracking(false);
      return;
    }

    const response = await fetch(`${API_BASE_URL}/api/journal/tracking/`, {
      credentials: "include",
      headers: trackingHeaders(),
    });

    if (!response.ok) {
      throw new Error("Tracking status request failed");
    }

    const result = await response.json();
    updateLocalTracking(Boolean(result.tracking));
  }, [updateLocalTracking]);

  const setTrackingEnabled = useCallback(
    async (enabled: boolean) => {
      const previousTracking = isTracking;
      updateLocalTracking(enabled);
      setIsTrackingPending(true);

      try {
        const response = await fetch(`${API_BASE_URL}/api/journal/tracking/`, {
          method: "POST",
          credentials: "include",
          headers: trackingHeaders(),
          body: JSON.stringify({ enabled }),
        });

        if (!response.ok) {
          throw new Error("Tracking request failed");
        }

        const result = await response.json();
        updateLocalTracking(Boolean(result.tracking));
      } catch (error) {
        updateLocalTracking(previousTracking);
        throw error;
      } finally {
        setIsTrackingPending(false);
      }
    },
    [isTracking, updateLocalTracking],
  );

  useEffect(() => {
    refreshTracking().catch(() => undefined);
  }, [refreshTracking]);

  const value = useMemo(
    () => ({
      isTracking,
      isTrackingPending,
      refreshTracking,
      setTrackingEnabled,
    }),
    [isTracking, isTrackingPending, refreshTracking, setTrackingEnabled],
  );

  return (
    <TrackingContext.Provider value={value}>{children}</TrackingContext.Provider>
  );
}

export function useTracking() {
  const value = useContext(TrackingContext);
  if (!value) {
    throw new Error("useTracking must be used inside TrackingProvider");
  }

  return value;
}
