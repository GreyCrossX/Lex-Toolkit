import { useEffect, useState } from "react";
import { apiMe, apiRefresh, type AuthUser } from "@/lib/auth-client";

type CustomerContext = {
  user: AuthUser | null;
  firmId: string | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
};

export function useCustomerContext(): CustomerContext {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        await apiRefresh().catch(() => null);
        const me = await apiMe();
        if (cancelled) return;
        setUser(me);
      } catch (err) {
        if (cancelled) return;
        setUser(null);
        setError(err instanceof Error ? err.message : "No se pudo obtener el usuario");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    user,
    firmId: user?.firm_id ?? null,
    loading,
    error,
    isAuthenticated: Boolean(user),
  };
}
