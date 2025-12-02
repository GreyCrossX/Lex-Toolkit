"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CircleCheck, CircleDashed, Loader2, LogOut, ShieldCheck, Sparkles } from "lucide-react";
import { useBackendHealth } from "@/hooks/use-backend-health";
import { API_BASE_URL } from "@/lib/config";
import { clearFakeToken, getFakeToken } from "@/lib/auth";
import { TOOLS, type Tool } from "@/lib/tools";

type ChatMessage = { role: "user" | "assistant"; content: string; ts: string };

export default function DashboardPage() {
  const health = useBackendHealth();
  const [pendingTool, setPendingTool] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<Tool>(TOOLS[0]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");

  const readyTools = useMemo(() => TOOLS.filter((t) => t.status === "ready"), []);
  const fakeToken = typeof window !== "undefined" ? getFakeToken() : null;

  const pingTool = async (tool: Tool) => {
    setPendingTool(tool.id);
    const signalUrl = `${API_BASE_URL}${tool.pingPath}`;

    try {
      const res = await fetch(signalUrl, { method: "GET" });

      if (!res.ok) {
        const message = `El endpoint respondió ${res.status}`;
        throw new Error(message);
      }

      toast.success(`${tool.name} está disponible`, {
        description: `Ping a ${tool.pingPath}`,
      });
    } catch (error) {
      console.error(`No se pudo alcanzar el backend para ${tool.id}`, error);
      toast.error("Backend no disponible", {
        description:
          error instanceof Error ? error.message : "No se pudo contactar la API. Revisa Docker/compose.",
      });
    } finally {
      setPendingTool(null);
    }
  };

  const onSelectTool = (tool: Tool) => {
    setSelectedTool(tool);
    pingTool(tool);
  };

  const onSend = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;
    const now = new Date().toISOString();
    const userMsg: ChatMessage = { role: "user", content: input.trim(), ts: now };
    const assistantMsg: ChatMessage = {
      role: "assistant",
      content:
        toolIsReady(selectedTool) && health === "online"
          ? "Respuesta placeholder. Conecta este chat al endpoint correspondiente para usar prompts y datasets."
          : "Esta herramienta aún no está lista; el backend sigue pendiente.",
      ts: now,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
  };

  return (
    <div className="min-h-screen bg-background px-6 py-8">
      <header className="mx-auto flex max-w-6xl flex-col gap-4 rounded-3xl border border-border/60 bg-surface/80 px-6 py-5 shadow-xl shadow-black/30 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-accent/40 bg-accent/15 text-xl font-semibold text-foreground">
            LT
          </div>
          <div>
            <p className="text-lg font-semibold text-foreground">Panel LexToolkit</p>
            <p className="text-sm text-muted">Selecciona una herramienta y conversa.</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={health} />
          <div className="rounded-full border border-border px-4 py-2 text-xs text-muted">
            Sesión: {fakeToken ? "JWT de demo en localStorage" : "Sin token"}
          </div>
          <button
            onClick={() => {
              clearFakeToken();
              toast.info("Sesión de demo eliminada");
            }}
            className="flex items-center gap-2 rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
          >
            <LogOut className="h-4 w-4" />
            Limpiar demo
          </button>
        </div>
      </header>

      <main className="mx-auto mt-8 max-w-6xl space-y-8">
        <section className="rounded-3xl border border-border/60 bg-surface/80 p-6 shadow-lg shadow-black/20">
          <nav className="flex flex-wrap gap-3 border-b border-border/60 pb-4">
            {TOOLS.map((tool) => (
              <button
                key={tool.id}
                onClick={() => onSelectTool(tool)}
                className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm transition ${
                  selectedTool.id === tool.id
                    ? "bg-accent text-contrast"
                    : "border border-border text-muted hover:border-accent hover:text-accent"
                }`}
              >
                <Sparkles className="h-4 w-4" />
                {tool.name}
              </button>
            ))}
          </nav>

          <div className="mt-6 grid gap-6 md:grid-cols-[1.1fr,0.9fr]">
            <div className="relative rounded-2xl border border-border/70 bg-card/70 p-4">
              <div className="flex items-center justify-between border-b border-border/60 pb-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted">Chat</p>
                  <p className="text-lg font-semibold text-foreground">{selectedTool.name}</p>
                  <p className="text-sm text-muted">
                    Envía un mensaje; si la herramienta no está lista, verás un placeholder.
                  </p>
                </div>
                {pendingTool === selectedTool.id && (
                  <div className="flex items-center gap-2 rounded-full border border-border bg-background/60 px-3 py-2 text-xs text-muted">
                    <Loader2 className="h-4 w-4 animate-spin text-accent" />
                    Probando endpoint...
                  </div>
                )}
              </div>

              <div className="mt-4 flex min-h-[280px] flex-col gap-3 rounded-xl bg-background/40 p-4">
                {messages.length === 0 ? (
                  <div className="rounded-xl border border-border/60 bg-card/80 p-4 text-sm text-muted">
                    Aún no hay mensajes. Escribe tu petición para {selectedTool.name}.
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <div
                      key={`${msg.ts}-${idx}`}
                      className={`max-w-xl rounded-xl border border-border/60 p-3 text-sm ${
                        msg.role === "user"
                          ? "self-end bg-accent/15 text-foreground border-accent/40"
                          : "self-start bg-card/70 text-muted"
                      }`}
                    >
                      <p className="text-[11px] uppercase tracking-wide text-muted">
                        {msg.role === "user" ? "Usuario" : "Asistente"}
                      </p>
                      <p className="mt-1 leading-relaxed text-foreground">{msg.content}</p>
                    </div>
                  ))
                )}
              </div>

              <form className="mt-4 flex gap-2" onSubmit={onSend}>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={`Pregúntale a ${selectedTool.name}...`}
                  className="flex-1 rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
                />
                <button
                  type="submit"
                  className="flex items-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong"
                >
                  Enviar
                </button>
              </form>
            </div>

            <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
              <p className="text-xs uppercase tracking-wide text-muted">Disponibilidad</p>
              <div className="mt-3 space-y-2">
                {readyTools.map((tool) => (
                  <div
                    key={tool.id}
                    className="flex items-center justify-between rounded-xl border border-border/60 bg-background/40 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-semibold text-foreground">{tool.name}</p>
                      <p className="text-xs text-muted">{tool.description}</p>
                    </div>
                    <button
                      onClick={() => pingTool(tool)}
                      className="rounded-full border border-accent/50 px-3 py-1 text-[11px] font-semibold text-accent transition hover:bg-accent/10"
                    >
                      Probar endpoint
                    </button>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex items-center gap-3 rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                <ShieldCheck className="h-5 w-5 text-accent" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Autenticación (nota)</p>
                  <p className="text-sm text-muted">
                    El UI está listo para JWT. Hoy solo guardamos un token de demo en localStorage sin middleware.
                  </p>
                </div>
              </div>

              <Link
                href="/"
                className="mt-4 inline-flex items-center rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
              >
                Volver al landing
              </Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function StatusBadge({ status }: { status: ReturnType<typeof useBackendHealth> }) {
  if (status === "checking") {
    return (
      <div className="flex items-center gap-2 rounded-full border border-border px-4 py-2 text-xs text-muted">
        <Loader2 className="h-4 w-4 animate-spin text-accent" />
        Verificando backend...
      </div>
    );
  }

  const isOnline = status === "online";

  return (
    <div
      className={`flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold ${
        isOnline ? "border-accent/50 text-accent" : "border-danger/40 text-danger"
      }`}
    >
      {isOnline ? <CircleCheck className="h-4 w-4" /> : <CircleDashed className="h-4 w-4" />}
      {isOnline ? "Backend en línea" : "Backend no disponible"}
    </div>
  );
}

function toolIsReady(tool: Tool) {
  return tool.status === "ready";
}
