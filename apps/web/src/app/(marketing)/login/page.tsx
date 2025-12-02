"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { setFakeToken } from "@/lib/auth";
import Link from "next/link";
import { LogIn, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);

    try {
      // Token falso solo para revisar UI.
      setFakeToken("demo-jwt-token");
      toast.success("Sesión de demo iniciada");
      router.push("/dashboard");
    } catch (error) {
      console.error("No se pudo establecer la sesión de demo", error);
      toast.error("No se pudo iniciar la sesión de demo");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="w-full max-w-md rounded-3xl border border-border/70 bg-surface/80 p-8 shadow-2xl shadow-black/30">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-accent/40 bg-accent/15 text-xl font-semibold text-foreground">
            LT
          </div>
          <div>
            <p className="text-lg font-semibold text-foreground">LexToolkit</p>
            <p className="text-sm text-muted">Acceso de demostración (JWT real próximamente)</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <label className="block">
            <span className="text-sm text-muted">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-2 w-full rounded-xl border border-border bg-card px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
              placeholder="maria@firm.com"
            />
          </label>

          <label className="block">
            <span className="text-sm text-muted">Contraseña</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-2 w-full rounded-xl border border-border bg-card px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
              placeholder="••••••••"
            />
          </label>

          <div className="flex items-center gap-2 rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-xs text-muted">
            <ShieldCheck className="h-4 w-4 text-accent" />
            La autenticación JWT reemplazará este flujo; hoy no enviamos credenciales al backend.
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-75"
          >
            <LogIn className="h-4 w-4" />
            {loading ? "Ingresando..." : "Entrar al panel"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-muted">
          Volver al{" "}
          <Link href="/" className="font-semibold text-accent hover:text-accent-strong">
            landing
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
