import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/config";
import { authFetch } from "@/lib/auth-fetch";

type HealthStatus = "checking" | "online" | "offline";

export function useServiceHealth(path: string, intervalMs = 30000) {
  const [status, setStatus] = useState<HealthStatus>("checking");
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const check = async () => {
      setStatus("checking");
      setError(null);
      try {
        const res = await authFetch(`${API_BASE_URL}${path}`, { method: "GET" });
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        if (cancelled) return;
        setStatus("online");
        setLastChecked(new Date());
      } catch (err) {
        if (cancelled) return;
        setStatus("offline");
        setError(err instanceof Error ? err.message : "Unknown error");
        setLastChecked(new Date());
      } finally {
        if (!cancelled) {
          timer = setTimeout(check, intervalMs);
        }
      }
    };

    check();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [path, intervalMs]);

  return { status, lastChecked, error };
}

export type { HealthStatus };
