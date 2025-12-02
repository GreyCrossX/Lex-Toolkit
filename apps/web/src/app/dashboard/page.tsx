"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CircleCheck, CircleDashed, Loader2, LogOut, ShieldCheck, Sparkles, Upload, Wand2 } from "lucide-react";
import { useBackendHealth } from "@/hooks/use-backend-health";
import { API_BASE_URL } from "@/lib/config";
import { clearFakeToken, getFakeToken } from "@/lib/auth";
import { TOOLS, type Tool } from "@/lib/tools";

type ChatMessage = { role: "user" | "assistant"; content: string; ts: string };
type Citation = {
  chunk_id: string;
  doc_id: string;
  section?: string | null;
  jurisdiction?: string | null;
  metadata?: Record<string, unknown>;
  content: string;
  distance?: number;
};
type SummaryResponse = { summary?: string; citations?: Citation[] };

export default function DashboardPage() {
  const health = useBackendHealth();
  const [pendingTool, setPendingTool] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<Tool>(TOOLS[0]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchDocIds, setSearchDocIds] = useState("");
  const [searchJurisdictions, setSearchJurisdictions] = useState("");
  const [searchSections, setSearchSections] = useState("");
  const [searchTopK, setSearchTopK] = useState(5);
  const [searchMode, setSearchMode] = useState<"qa" | "search">("qa");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchAnswer, setSearchAnswer] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<Citation[]>([]);
  const [searchPage, setSearchPage] = useState(1);
  const [searchPageSize] = useState(5);
  const [summaryInput, setSummaryInput] = useState("");
  const [summaryOutput, setSummaryOutput] = useState<string | null>(null);
  const [summaryCitations, setSummaryCitations] = useState<Citation[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [uploadName, setUploadName] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [sortByScoreAsc, setSortByScoreAsc] = useState(true);
  const [citationsPage, setCitationsPage] = useState(1);
  const [citationsPageSize] = useState(5);

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
    const assistantMsg: ChatMessage =
      selectedTool.status === "ready" && health === "online"
        ? {
            role: "assistant",
            content:
              "Placeholder. Conecta este chat al endpoint correspondiente para usar prompts y datasets (usa /qa para respuestas con citas).",
            ts: now,
          }
        : {
            role: "assistant",
            content: "Esta herramienta aún no está lista; el backend sigue pendiente.",
            ts: now,
          };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
  };

  const runSearch = async () => {
    setSearchLoading(true);
    if (searchMode === "qa") setSearchAnswer(null);
    setSearchResults([]);
    setCitationsPage(1);
    setSearchPage(1);

    try {
      const body =
        searchMode === "qa"
          ? {
              query: searchQuery,
              top_k: searchTopK,
              doc_ids: formatList(searchDocIds),
              jurisdictions: formatList(searchJurisdictions),
              sections: formatList(searchSections),
              max_distance: 1.5,
            }
          : {
              query: searchQuery,
              limit: searchTopK,
              doc_ids: formatList(searchDocIds),
              jurisdictions: formatList(searchJurisdictions),
              sections: formatList(searchSections),
              max_distance: 1.5,
            };

      const endpoint = searchMode === "qa" ? "/qa" : "/search";

      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const message = `Respuesta ${res.status}`;
        throw new Error(message);
      }

      const data = (await res.json()) as {
        answer?: string;
        citations?: Citation[];
      };

      setSearchAnswer(data.answer ?? null);
      const sorted = (data.citations ?? []).sort((a, b) => {
        if (a.distance === undefined || b.distance === undefined) return 0;
        return sortByScoreAsc ? a.distance - b.distance : b.distance - a.distance;
      });
      setSearchResults(sorted);
      toast.success(searchMode === "qa" ? "Q&A ejecutado" : "Búsqueda ejecutada");
    } catch (error) {
      console.error("Error en búsqueda/QA", error);
      toast.error("No se pudo ejecutar la búsqueda", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
    } finally {
      setSearchLoading(false);
    }
  };

  const runSummary = async () => {
    if (!summaryInput.trim()) {
      toast.info("Escribe un texto para resumir");
      return;
    }
    setSummaryLoading(true);
    setSummaryOutput(null);
    setSummaryCitations([]);
    try {
      const res = await fetch(`${API_BASE_URL}/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: summaryInput }),
      });

      if (!res.ok) {
        throw new Error(`Respuesta ${res.status}`);
      }

      const data = (await res.json()) as SummaryResponse;
      setSummaryOutput(data.summary ?? "Resumen generado sin contenido");
      setSummaryCitations(data.citations ?? []);
      toast.success("Resumen generado");
    } catch (error) {
      console.error("Error en resumen", error);
      const snippet = summaryInput.slice(0, 240);
      setSummaryOutput(`Resumen placeholder (conecta a /summary): ${snippet}...`);
      toast.error("No se pudo generar el resumen; usando placeholder", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
    } finally {
      setSummaryLoading(false);
    }
  };

  const runUpload = async (file: File) => {
    setUploading(true);
    setUploadStatus(null);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Respuesta ${res.status}`);
      }

      toast.success("Documento cargado");
      setUploadStatus("Documento enviado. Esperando ingesta...");
    } catch (error) {
      console.error("Error en carga", error);
      toast.error("No se pudo cargar el documento", {
        description:
          error instanceof Error
            ? error.message
            : "Endpoint de ingesta no disponible. Conectar cuando exista.",
      });
      setUploadStatus("Endpoint no disponible (placeholder).");
    } finally {
      setUploading(false);
    }
  };

  const paginatedCitations = searchResults.slice(
    (citationsPage - 1) * citationsPageSize,
    citationsPage * citationsPageSize
  );
  const paginatedResults = searchResults.slice((searchPage - 1) * searchPageSize, searchPage * searchPageSize);

  const renderToolContent = () => {
    if (selectedTool.id === "search" || selectedTool.id === "qa") {
      return (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3 text-xs text-muted">
            <button
              onClick={() => setSearchMode("qa")}
              className={`rounded-full border px-3 py-1 ${
                searchMode === "qa" ? "border-accent text-accent bg-accent/10" : "border-border"
              }`}
            >
              Q&A (respuesta + citas)
            </button>
            <button
              onClick={() => setSearchMode("search")}
              className={`rounded-full border px-3 py-1 ${
                searchMode === "search" ? "border-accent text-accent bg-accent/10" : "border-border"
              }`}
            >
              Búsqueda (lista de resultados)
            </button>
            <span className="rounded-full border border-border px-3 py-1">
              Endpoint: {searchMode === "qa" ? "/qa" : "/qa (placeholder para /search)"}
            </span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm text-muted">
              Pregunta o consulta
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Ej. requisitos para licitaciones en CDMX"
                className="rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted">
              Doc IDs (coma)
              <input
                value={searchDocIds}
                onChange={(e) => setSearchDocIds(e.target.value)}
                placeholder="doc123, doc456"
                className="rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted">
              Jurisdicciones (coma)
              <input
                value={searchJurisdictions}
                onChange={(e) => setSearchJurisdictions(e.target.value)}
                placeholder="cdmx, federal"
                className="rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted">
              Secciones (coma)
              <input
                value={searchSections}
                onChange={(e) => setSearchSections(e.target.value)}
                placeholder="artículo, capítulo"
                className="rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted">
              Resultados (top_k)
              <input
                type="number"
                min={1}
                max={20}
                value={searchTopK}
                onChange={(e) => setSearchTopK(Number(e.target.value))}
                className="rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
              />
            </label>
          </div>
          <button
            onClick={runSearch}
            disabled={searchLoading || !searchQuery.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-70"
          >
            <Wand2 className="h-4 w-4" />
            {searchLoading ? "Buscando..." : "Ejecutar búsqueda / Q&A"}
          </button>

          <div className="rounded-xl border border-border/60 bg-background/40 p-4">
            <p className="text-sm font-semibold text-foreground">
              {searchMode === "qa" ? "Respuesta" : "Resultados"}
            </p>
            {searchMode === "qa" ? (
              <p className="mt-2 text-sm text-muted">
                {searchAnswer ?? "Sin respuesta aún. Ejecuta una consulta para ver contenido."}
              </p>
            ) : (
              <p className="mt-2 text-sm text-muted">
                Resultados listados abajo (ahora usando /search con embedding server-side).
              </p>
            )}
          </div>

          <div className="rounded-xl border border-border/60 bg-background/40 p-4">
            <p className="text-sm font-semibold text-foreground">
              {searchMode === "qa" ? "Citas" : "Resultados"}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted">
              <button
                className="rounded-full border border-border px-3 py-1 hover:border-accent hover:text-accent"
                onClick={() => {
                  setSortByScoreAsc((prev) => !prev);
                  setSearchResults((prev) => {
                    const sorted = [...prev].sort((a, b) => {
                      if (a.distance === undefined || b.distance === undefined) return 0;
                      return !sortByScoreAsc ? a.distance - b.distance : b.distance - a.distance;
                    });
                    return sorted;
                  });
                }}
              >
                Ordenar por distancia {sortByScoreAsc ? "↑" : "↓"}
              </button>
              <span>
                Página {citationsPage} / {Math.max(1, Math.ceil(searchResults.length / citationsPageSize))}
              </span>
              <div className="flex items-center gap-1">
                <button
                  disabled={citationsPage === 1}
                  onClick={() => setCitationsPage((p) => Math.max(1, p - 1))}
                  className="rounded-full border border-border px-2 py-1 disabled:opacity-50"
                >
                  ◀
                </button>
                <button
                  disabled={citationsPage >= Math.max(1, Math.ceil(searchResults.length / citationsPageSize))}
                  onClick={() =>
                    setCitationsPage((p) =>
                      Math.min(Math.max(1, Math.ceil(searchResults.length / citationsPageSize)), p + 1)
                    )
                  }
                  className="rounded-full border border-border px-2 py-1 disabled:opacity-50"
                >
                  ▶
                </button>
              </div>
            </div>

            {searchMode === "search" && paginatedResults.length > 0 && (
              <div className="mt-3 overflow-hidden rounded-lg border border-border/60">
                <table className="w-full text-left text-sm text-muted">
                  <thead className="bg-card/80 text-xs uppercase tracking-wide text-muted">
                    <tr>
                      <th className="px-3 py-2">Doc</th>
                      <th className="px-3 py-2">Sección</th>
                      <th className="px-3 py-2">Jurisdicción</th>
                      <th className="px-3 py-2">Distancia</th>
                      <th className="px-3 py-2">Fragmento</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedResults.map((r) => (
                      <tr key={r.chunk_id} className="border-t border-border/60">
                        <td className="px-3 py-2 text-foreground">{r.doc_id}</td>
                        <td className="px-3 py-2">{r.section ?? "—"}</td>
                        <td className="px-3 py-2">{r.jurisdiction ?? "—"}</td>
                        <td className="px-3 py-2">{r.distance !== undefined ? r.distance.toFixed(3) : "—"}</td>
                        <td className="px-3 py-2 text-foreground">{r.content}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {paginatedCitations.length === 0 && searchMode === "qa" ? (
              <p className="text-sm text-muted">Sin citas aún.</p>
            ) : null}

            {searchMode === "qa" && paginatedCitations.length > 0 && (
              <ul className="mt-3 space-y-3 text-sm text-muted">
                {paginatedCitations.map((c) => (
                  <li key={c.chunk_id} className="rounded-lg border border-border/60 bg-card/70 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted">
                      {c.doc_id} • {c.section ?? "sección"} • {c.jurisdiction ?? "jurisdicción"}
                    </p>
                    <p className="mt-1 text-foreground">{c.content}</p>
                    {c.distance !== undefined && (
                      <p className="text-[11px] text-muted">distancia: {c.distance.toFixed(3)}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      );
    }

    if (selectedTool.id === "upload") {
      return (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Carga de documentos hacia el backend de ingesta (intentará llamar a /upload). Si no existe el endpoint,
            verás un error y mensaje de placeholder.
          </p>
          <label className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/70 bg-background/30 p-6 text-sm text-muted">
            <Upload className="h-6 w-6 text-accent" />
            <span>{uploadName ?? "Arrastra un PDF o haz clic para seleccionar"}</span>
            <input
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                if (!e.target.files?.length) return;
                const file = e.target.files[0];
                setUploadName(file.name);
                runUpload(file);
              }}
            />
          </label>
          {uploadStatus && <p className="text-sm text-muted">{uploadStatus}</p>}
          <button
            disabled={uploading}
            onClick={() => toast.info("Elige un archivo para subir")}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-70"
          >
            Registrar documento
          </button>
        </div>
      );
    }

    if (selectedTool.id === "summary-single" || selectedTool.id === "summary-multi") {
      return (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Resumen usando `/summary` (si está disponible). Pega texto o selecciona un doc; si falla, verás un
            placeholder.
          </p>
          <textarea
            value={summaryInput}
            onChange={(e) => setSummaryInput(e.target.value)}
            rows={6}
            placeholder="Pega texto a resumir..."
            className="w-full rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
          />
          <button
            onClick={runSummary}
            disabled={summaryLoading}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-70"
          >
            <Wand2 className="h-4 w-4" />
            {summaryLoading ? "Resumiendo..." : "Generar resumen"}
          </button>
          <div className="rounded-xl border border-border/60 bg-background/40 p-4">
            <p className="text-sm font-semibold text-foreground">Salida</p>
            <p className="mt-2 text-sm text-muted">
              {summaryOutput ?? "Aún no hay resumen. Ejecuta para ver el placeholder."}
            </p>
            {summaryCitations.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-xs uppercase tracking-wide text-muted">Citas</p>
                <ul className="space-y-2 text-sm text-muted">
                  {summaryCitations.map((c) => (
                    <li key={c.chunk_id} className="rounded-lg border border-border/60 bg-card/70 p-2">
                      <p className="text-xs uppercase tracking-wide text-muted">
                        {c.doc_id} • {c.section ?? "sección"} • {c.jurisdiction ?? "jurisdicción"}
                      </p>
                      <p className="mt-1 text-foreground">{c.content}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-4">
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
    );
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
                  <p className="text-xs uppercase tracking-wide text-muted">Herramienta</p>
                  <p className="text-lg font-semibold text-foreground">{selectedTool.name}</p>
                  <p className="text-sm text-muted">
                    {selectedTool.status === "ready"
                      ? "Disponible para probar."
                      : "Placeholder de UI hasta que el backend esté listo."}
                  </p>
                </div>
                {pendingTool === selectedTool.id && (
                  <div className="flex items-center gap-2 rounded-full border border-border bg-background/60 px-3 py-2 text-xs text-muted">
                    <Loader2 className="h-4 w-4 animate-spin text-accent" />
                    Probando endpoint...
                  </div>
                )}
              </div>

              {renderToolContent()}
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

function formatList(value: string) {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

export { formatList };
