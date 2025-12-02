import { useEffect, useState } from "react";
import { toast } from "sonner";
import { API_BASE_URL } from "@/lib/config";

export type HealthStatus = "checking" | "online" | "offline";

export function useBackendHealth() {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
        if (cancelled) return;

        if (res.ok) {
          setStatus("online");
        } else {
          setStatus("offline");
          toast.error("Backend no disponible", {
            description: `Healthcheck devolvió ${res.status}`,
          });
        }
      } catch (error) {
        if (cancelled) return;
        console.error("Fallo el healthcheck de backend", error);
        setStatus("offline");
        toast.error("Backend no disponible", {
          description: "No pudimos contactar la API. Revisa Docker/compose.",
        });
      }
    };

    check();

    return () => {
      cancelled = true;
    };
  }, []);

  return status;
}
