"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  ArrowLeftRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  LogOut,
  Menu,
  ShieldCheck,
  Sparkles,
  Upload,
  Wand2,
  X,
} from "lucide-react";
import { useBackendHealth } from "@/hooks/use-backend-health";
import { useServiceHealth } from "@/hooks/use-service-health";
import { useCustomerContext } from "@/hooks/use-customer-context";
import { API_BASE_URL } from "@/lib/config";
import { clearAccessToken, getAccessToken } from "@/lib/auth";
import { authFetch } from "@/lib/auth-fetch";
import { apiLogout } from "@/lib/auth-client";
import { TOOLS, type Tool } from "@/lib/tools";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  results?: Citation[];
  meta?: { tool: string; mode?: string };
};
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
type UploadJobStatus = "queued" | "uploading" | "processing" | "completed" | "failed";
type UploadResponsePayload = { job_id: string; status: UploadJobStatus; message?: string };
type UploadStatusPayload = {
  job_id: string;
  filename: string;
  status: UploadJobStatus;
  progress?: number;
  message?: string;
  error?: string;
  doc_ids?: string[];
};

const SEARCH_PLACEHOLDER = "Ej. requisitos para licitaciones en CDMX";
const SUMMARY_PLACEHOLDER = "Pega texto a resumir...";

export const formatList = (value: string) =>
  value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);

export default function DashboardPage() {
  const health = useBackendHealth();
  const summaryHealth = useServiceHealth("/summary/health", 30000);
  const { user, firmId, loading: userLoading, error: userError } = useCustomerContext();
  const [selectedTool, setSelectedTool] = useState<Tool>(TOOLS.find((t) => t.id === "qa") || TOOLS[0]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchDocIds, setSearchDocIds] = useState("");
  const [searchJurisdictions, setSearchJurisdictions] = useState("");
  const [searchSections, setSearchSections] = useState("");
  const [searchTopK, setSearchTopK] = useState(5);
  const [searchMode, setSearchMode] = useState<"qa" | "search">("qa");
  const [summaryDocIds, setSummaryDocIds] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [summaryBuffer, setSummaryBuffer] = useState("");
  const [summaryFileName, setSummaryFileName] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState(() => getAccessToken());
  const [uploadName, setUploadName] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadDocIds, setUploadDocIds] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [citationSortDesc, setCitationSortDesc] = useState(false);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const activeUploadJobId = useRef<string | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);
  const [summaryDragActive, setSummaryDragActive] = useState(false);
  const [uploadDragActive, setUploadDragActive] = useState(false);

  const readyTools = useMemo(() => TOOLS.filter((t) => t.status === "ready"), []);
  const syncSessionToken = () => setSessionToken(getAccessToken());

  useEffect(() => {
    const el = chatBottomRef.current;
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, actionLoading]);

  useEffect(() => {
    if (userError) {
      toast.error("No se pudo obtener tu sesión", {
        description: userError,
      });
    }
  }, [userError]);

  const pushMessage = (msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  };

  const onSelectTool = (tool: Tool) => {
    setSelectedTool(tool);
    setSidebarOpen(false);
  };

  const runQAOrSearch = async (query: string) => {
    setActionLoading(true);
    const body =
      searchMode === "qa"
        ? {
            query,
            top_k: searchTopK,
            doc_ids: formatList(searchDocIds),
            jurisdictions: formatList(searchJurisdictions),
            sections: formatList(searchSections),
            max_distance: 1.5,
          }
        : {
            query,
            limit: searchTopK,
            doc_ids: formatList(searchDocIds),
            jurisdictions: formatList(searchJurisdictions),
            sections: formatList(searchSections),
            max_distance: 1.5,
          };
    const endpoint = searchMode === "qa" ? "/qa" : "/search";
    try {
      const res = await authFetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Respuesta ${res.status}`);
      const data = (await res.json()) as { answer?: string; citations?: Citation[]; results?: Citation[] };
      const sortedCitations = (data.citations ?? []).slice().sort((a, b) => {
        const aDist = a.distance ?? Number.POSITIVE_INFINITY;
        const bDist = b.distance ?? Number.POSITIVE_INFINITY;
        return aDist - bDist;
      });
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content:
          searchMode === "qa"
            ? data.answer ?? "Sin respuesta."
            : `Resultados de búsqueda (${(data.results ?? data.citations ?? []).length})`,
        citations: searchMode === "qa" ? sortedCitations : undefined,
        results: searchMode === "search" ? data.results ?? sortedCitations : undefined,
        meta: { tool: searchMode, mode: searchMode },
      };
      pushMessage(assistantMsg);
      syncSessionToken();
    } catch (error) {
      console.error("Error en búsqueda/QA", error);
      toast.error("No se pudo ejecutar la consulta", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const runSummary = async (text: string) => {
    setSummaryLoading(true);
    setActionLoading(true);
    const docIds = formatList(summaryDocIds);
    const payload = { text, doc_ids: docIds.length > 0 ? docIds : undefined, stream: true };
    let assembled = "";
    const citations: Citation[] = [];

    const consumeStream = async (res: Response) => {
      if (!res.body) {
        const data = (await res.json()) as SummaryResponse;
        assembled = data.summary ?? "";
        citations.push(...(data.citations ?? []));
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const evt = JSON.parse(trimmed) as { type: string; data: unknown };
            if (evt.type === "citation" && evt.data) {
              citations.push(evt.data as Citation);
            } else if (evt.type === "summary_chunk" && typeof evt.data === "string") {
              assembled += evt.data;
            }
          } catch (err) {
            console.error("No se pudo parsear evento de resumen", err);
          }
        }
      }
    };

    try {
      const res = await authFetch(`${API_BASE_URL}/summary/document`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Respuesta ${res.status}`);
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/x-ndjson")) {
        await consumeStream(res);
      } else {
        const data = (await res.json()) as SummaryResponse;
        assembled = data.summary ?? "";
        citations.push(...(data.citations ?? []));
      }
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: assembled || "(sin contenido)",
        citations,
        meta: { tool: "summary" },
      };
      pushMessage(assistantMsg);
      toast.success("Resumen listo");
      syncSessionToken();
    } catch (error) {
      console.error("Error en resumen", error);
      toast.error("No se pudo generar el resumen", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
      pushMessage({
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "Resumen placeholder",
        meta: { tool: "summary" },
      });
    } finally {
      setSummaryLoading(false);
      setActionLoading(false);
    }
  };

  const onSend = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    const now = new Date().toISOString();
    pushMessage({ id: `user-${now}`, role: "user", content: text });
    setInput("");
    if (selectedTool.id === "research") {
      await runQAOrSearch(text);
    } else if (selectedTool.id === "summary") {
      toast.info("Usa el dropzone de resumen para cargar texto o .txt.");
    } else if (selectedTool.id === "communication") {
      await runQAOrSearch(text);
    } else {
      pushMessage({
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "Esta herramienta aún no está conectada.",
      });
    }
  };

  const resetUpload = () => {
    setUploadName(null);
    setUploadStatus(null);
    setUploadProgress(0);
    setUploadDocIds([]);
    setUploadError(null);
    setUploading(false);
    activeUploadJobId.current = null;
  };

  const pollUploadStatus = async (jobId: string, attempt = 0) => {
    if (activeUploadJobId.current !== jobId) return;
    try {
      const res = await authFetch(`${API_BASE_URL}/upload/${jobId}`);
      if (!res.ok) throw new Error(`Respuesta ${res.status}`);
      const data = (await res.json()) as UploadStatusPayload;
      setUploadStatus(data.message ?? `Estado: ${data.status}`);
      setUploadProgress(data.progress ?? 0);
      setUploadDocIds(data.doc_ids ?? []);
      syncSessionToken();
      if (data.status === "completed") {
        setUploading(false);
        activeUploadJobId.current = null;
        toast.success("Ingesta completada", { description: data.message ?? "Listo para búsqueda." });
        return;
      }
      if (data.status === "failed") {
        setUploading(false);
        activeUploadJobId.current = null;
        const message = data.error ?? "Error en ingesta.";
        setUploadError(message);
        toast.error("Ingesta fallida", { description: message });
        return;
      }
      setTimeout(() => pollUploadStatus(jobId, attempt + 1), 150);
    } catch (error) {
      console.error("Error al consultar estatus de ingesta", error);
      if (attempt >= 4) {
        setUploading(false);
        activeUploadJobId.current = null;
        const message =
          error instanceof Error ? error.message : "No se pudo consultar el estado de la ingesta (placeholder).";
        setUploadError(message);
        toast.error("No se pudo consultar ingesta", { description: message });
        return;
      }
      setTimeout(() => pollUploadStatus(jobId, attempt + 1), 200);
    }
  };

  const handleSummaryFile = (file: File) => {
    if (file.type !== "text/plain") {
      toast.error("Solo archivos .txt por ahora para resumen directo. Si es PDF, pega el texto.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : "";
      setSummaryBuffer(text);
      setSummaryFileName(file.name);
      toast.success("Texto cargado para resumen", { description: file.name });
    };
    reader.readAsText(file);
  };

  const runUpload = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    setUploadStatus(null);
    setUploadProgress(0);
    setUploadDocIds([]);
    setUploadStatus("Preparando archivo para ingesta...");
    activeUploadJobId.current = null;

    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await authFetch(`${API_BASE_URL}/upload`, { method: "POST", body: formData });
      if (!res.ok) throw new Error(`Respuesta ${res.status}`);
      const data = (await res.json()) as UploadResponsePayload;
      if (!data.job_id) throw new Error("Respuesta de ingesta inválida (sin job_id).");
      activeUploadJobId.current = data.job_id;
      setUploadStatus(data.message ?? "Trabajo en cola.");
      setUploadProgress(5);
      syncSessionToken();
      toast.success("Documento enviado", { description: "Seguimiento de ingesta en progreso." });
      pollUploadStatus(data.job_id);
    } catch (error) {
      console.error("Error en carga", error);
      const description =
        error instanceof Error ? error.message : "Endpoint de ingesta no disponible. Conectar cuando exista.";
      toast.error("No se pudo cargar el documento", { description });
      setUploadStatus(null);
      setUploadError(description);
      setUploading(false);
    }
  };

  const renderMessage = (msg: ChatMessage) => {
    const citations = msg.citations
      ? citationSortDesc
        ? [...msg.citations].reverse()
        : msg.citations
      : null;
    const results = msg.results
      ? citationSortDesc
        ? [...msg.results].reverse()
        : msg.results
      : null;

    return (
      <div
        key={msg.id}
        className={`max-w-3xl rounded-2xl border border-border/60 px-4 py-3 text-sm shadow-sm ${
          msg.role === "user" ? "self-end bg-accent/10 text-foreground border-accent/30" : "self-start bg-card/80 text-muted"
        }`}
      >
        <p className="text-[11px] uppercase tracking-wide text-muted">
          {msg.role === "user" ? "Usuario" : msg.meta?.tool ? `Asistente · ${msg.meta.tool}` : "Asistente"}
        </p>
        <p className="mt-2 whitespace-pre-wrap leading-relaxed text-foreground">{msg.content}</p>
        {citations && citations.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-[11px] uppercase tracking-wide text-muted">Citas</p>
            <ul className="space-y-2">
              {citations.map((c) => (
                <li key={c.chunk_id} className="rounded-lg border border-border/60 bg-background/60 p-2">
                  <p className="text-[12px] text-muted">
                    <span className="font-semibold">{c.doc_id}</span> • {c.section ?? "sección"} •{" "}
                    {c.jurisdiction ?? "jurisdicción"} •{" "}
                    {c.distance !== undefined ? c.distance.toFixed(3) : "—"}
                  </p>
                  <p className="text-foreground">{c.content}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
        {results && results.length > 0 && (
          <div className="mt-3">
            <p className="text-[11px] uppercase tracking-wide text-muted">Resultados</p>
            <ul className="mt-1 space-y-2 text-muted">
              {results.map((r) => (
                <li key={r.chunk_id} className="rounded-lg border border-border/60 bg-background/60 p-2">
                  <p className="text-[12px] text-muted">
                    <span className="font-semibold">{r.doc_id}</span> • {r.section ?? "sección"} •{" "}
                    {r.jurisdiction ?? "jurisdicción"} •{" "}
                    {r.distance !== undefined ? r.distance.toFixed(3) : "—"}
                  </p>
                  <p className="text-foreground">{r.content}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const StatusBadge = ({ status }: { status: "online" | "offline" | "checking" }) => {
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
          isOnline ? "border-emerald-500/40 text-emerald-300" : "border-danger/40 text-danger"
        }`}
      >
        {isOnline ? <CheckCircle2 className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
        {isOnline ? "Backend en línea" : "Backend no disponible"}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-border/50 bg-surface/80 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <button
            className="flex h-10 w-10 items-center justify-center rounded-full border border-border text-sm text-foreground transition hover:border-accent hover:text-accent md:hidden"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label="Toggle sidebar"
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <Link
            href="/"
            className="flex h-12 w-12 items-center justify-center rounded-xl border border-accent/40 bg-accent/15 text-xl font-semibold text-foreground"
          >
            LT
          </Link>
          <div className="hidden md:block">
            <p className="text-lg font-semibold text-foreground">Panel LexToolkit</p>
            <p className="text-sm text-muted">Selecciona una herramienta y conversa.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={health} />
          <div className="hidden rounded-full border border-border px-4 py-2 text-xs text-muted md:flex">
            {userLoading
              ? "Verificando sesión..."
              : user
                ? `${user.full_name || user.email}${firmId ? ` · ${firmId}` : ""}`
                : "No autenticado"}
          </div>
          <button
            onClick={async () => {
              try {
                await apiLogout();
                clearAccessToken();
                setSessionToken(null);
                toast.info("Sesión cerrada");
              } catch (error) {
                console.error("No se pudo cerrar sesión", error);
                toast.error("No se pudo cerrar sesión", {
                  description: error instanceof Error ? error.message : "Error desconocido",
                });
              }
            }}
            className="hidden items-center gap-2 rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent md:flex"
          >
            <LogOut className="h-4 w-4" />
            Cerrar sesión
          </button>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-64px)]">
        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-30 w-72 transform border-r border-border/60 bg-surface/90 p-4 transition-transform duration-300 md:relative md:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
          }`}
        >
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">Herramientas</p>
            <button
              className="md:hidden text-muted"
              aria-label="Cerrar"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="space-y-2">
            {readyTools.map((tool) => (
              <button
                key={tool.id}
                aria-label={tool.ariaLabel || tool.name}
                onClick={() => onSelectTool(tool)}
                className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-left text-sm transition ${
                  selectedTool.id === tool.id
                    ? "border-accent bg-accent/10 text-foreground"
                    : "border-border text-muted hover:border-accent hover:text-accent"
                }`}
              >
                <span>{tool.name}</span>
                {tool.id === "summary" && (
                  <span
                    className={`h-2 w-2 rounded-full ${
                      summaryHealth.status === "online"
                        ? "bg-emerald-400"
                        : summaryHealth.status === "checking"
                          ? "bg-amber-300"
                          : "bg-red-400"
                    }`}
                  />
                )}
              </button>
            ))}
          </div>

          <div className="mt-6 space-y-3 rounded-2xl border border-border/60 bg-card/70 p-3 text-sm text-muted">
            <button
              className="flex w-full items-center justify-between text-foreground"
              onClick={() => setFiltersOpen((v) => !v)}
            >
              <span className="flex items-center gap-2">
                <ArrowLeftRight className="h-4 w-4" />
                Filtros avanzados
              </span>
              {filtersOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            {filtersOpen && (
              <div className="space-y-3 pt-2">
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Doc IDs (coma)</span>
                  <input
                    value={searchDocIds}
                    onChange={(e) => setSearchDocIds(e.target.value)}
                    placeholder="doc123, doc456"
                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus:border-accent"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Jurisdicciones (coma)</span>
                  <input
                    value={searchJurisdictions}
                    onChange={(e) => setSearchJurisdictions(e.target.value)}
                    placeholder="cdmx, federal"
                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus:border-accent"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Secciones (coma)</span>
                  <input
                    value={searchSections}
                    onChange={(e) => setSearchSections(e.target.value)}
                    placeholder="artículo, capítulo"
                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus:border-accent"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Resultados (top_k)</span>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={searchTopK}
                    onChange={(e) => setSearchTopK(Number(e.target.value))}
                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus:border-accent"
                  />
                </label>
                <div className="flex items-center gap-2 text-xs text-muted">
                  <button
                    onClick={() => setSearchMode("qa")}
                    aria-label="Q&A"
                    className={`rounded-full border px-3 py-1 ${
                      searchMode === "qa" ? "border-accent text-accent" : "border-border"
                    }`}
                  >
                    Q&A
                  </button>
                  <button
                    onClick={() => setSearchMode("search")}
                    aria-label="Búsqueda (lista de resultados)"
                    className={`rounded-full border px-3 py-1 ${
                      searchMode === "search" ? "border-accent text-accent" : "border-border"
                    }`}
                  >
                    Búsqueda
                  </button>
                </div>
                <div className="rounded-xl border border-border/60 bg-background/60 p-3 text-xs">
                  <p className="font-semibold text-foreground">Resumen (doc_ids opcionales)</p>
                  <input
                    value={summaryDocIds}
                    onChange={(e) => setSummaryDocIds(e.target.value)}
                    placeholder="doc123, doc456 (resumen)"
                    className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus:border-accent"
                  />
                  <p className="mt-1 text-muted">/summary/health: {summaryHealth.status}</p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 space-y-2 rounded-2xl border border-border/60 bg-card/70 p-3 text-sm text-muted">
            <div className="flex items-center gap-2 text-foreground">
              <Upload className="h-4 w-4" />
              <span>Subir documento</span>
            </div>
            <div
              className={`flex cursor-pointer flex-col gap-2 rounded-xl border border-dashed p-3 text-xs transition ${
                uploadDragActive ? "border-accent bg-accent/5" : "border-border/60 bg-background/60"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setUploadDragActive(true);
              }}
              onDragLeave={() => setUploadDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setUploadDragActive(false);
                const file = e.dataTransfer.files?.[0];
                if (file) {
                  setUploadName(file.name);
                  runUpload(file);
                }
              }}
              onClick={() => uploadInputRef.current?.click()}
            >
              <p className="text-foreground">Arrastra o selecciona un PDF</p>
              <p className="text-muted">Ingesta y tracking automático.</p>
              <input
                ref={uploadInputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setUploadName(file.name);
                  runUpload(file);
                }}
                disabled={uploading}
              />
            </div>
            {uploadName && <p className="text-xs text-muted">Archivo: {uploadName}</p>}
            {selectedTool.id !== "upload" && (uploadStatus || uploadError) && (
              <div className="rounded-lg border border-border/60 bg-background/70 p-2 text-xs text-muted">
                <p>{uploadStatus ?? "No se pudo iniciar la ingesta."}</p>
                <div className="mt-1 h-2 w-full rounded-full bg-border/50">
                  <div
                    className="h-2 rounded-full bg-accent"
                    style={{ width: `${Math.min(uploadProgress, 100)}%` }}
                  />
                </div>
                {uploadDocIds.length > 0 && <p className="mt-1">Doc IDs: {uploadDocIds.join(", ")}</p>}
                {uploadError && <p className="mt-1 text-danger">Error: {uploadError}</p>}
                <button
                  className="mt-2 text-foreground underline"
                  onClick={resetUpload}
                  type="button"
                  disabled={uploading}
                >
                  Limpiar
                </button>
              </div>
            )}
          </div>
        </aside>

        {/* Main chat area */}
        <main className="flex flex-1 flex-col bg-background px-4 py-4 md:ml-0 md:px-8">
          <div className="mb-3 flex items-center gap-2 rounded-full border border-accent/50 bg-accent/10 px-4 py-2 text-sm font-semibold text-foreground shadow-sm">
            <Sparkles className="h-4 w-4 text-accent" />
            <span>{selectedTool.name}</span>
            <span className="rounded-full bg-card/60 px-2 py-1 text-[11px] font-normal text-muted">
              {selectedTool.description}
            </span>
          </div>

          <div className="mb-2 flex justify-end">
            <button
              type="button"
              aria-label="Ordenar por distancia"
              onClick={() => setCitationSortDesc((v) => !v)}
              className="rounded-full border border-border px-3 py-1 text-xs text-muted transition hover:border-accent hover:text-accent"
            >
              Ordenar por distancia {citationSortDesc ? "(desc)" : "(asc)"}
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-2xl border border-border/60 bg-surface/80 p-4">
            {messages.length === 0 ? (
              <div className="rounded-xl border border-border/60 bg-card/80 p-4 text-sm text-muted">
                Aún no hay mensajes. Escribe tu petición para {selectedTool.name}. Usa filtros a la izquierda para
                acotar doc_ids, jurisdicciones y secciones.
              </div>
            ) : (
              messages.map(renderMessage)
            )}
            {actionLoading && (
              <div className="flex items-center gap-2 text-sm text-muted">
                <Loader2 className="h-4 w-4 animate-spin text-accent" />
                Procesando...
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {selectedTool.id === "summary" ? (
            <div className="sticky bottom-2 mt-3 rounded-2xl border border-border/60 bg-card/90 p-4 shadow-lg">
              <textarea
                value={summaryBuffer}
                onChange={(e) => setSummaryBuffer(e.target.value)}
                placeholder={SUMMARY_PLACEHOLDER}
                rows={4}
                className="w-full resize-none rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
              />
              <p className="mt-1 text-[11px] text-muted">Pega texto o adjunta un .txt.</p>
              <div
                className={`flex flex-col gap-2 rounded-xl border border-dashed p-3 text-sm ${
                  summaryDragActive ? "border-accent bg-accent/5" : "border-border/70 bg-background/60"
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setSummaryDragActive(true);
                }}
                onDragLeave={() => setSummaryDragActive(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setSummaryDragActive(false);
                  const file = e.dataTransfer.files?.[0];
                  if (file) handleSummaryFile(file);
                }}
              >
                <div className="flex items-center gap-2 text-foreground">
                  <FileText className="h-4 w-4 text-accent" />
                  <span className="font-semibold">Arrastra un .txt o selecciona un documento</span>
                </div>
                <p className="text-xs text-muted">
                  Cargaremos el texto y lo resumiremos. Para PDF pega el texto manualmente (sin input visible).
                </p>
                <input
                  type="file"
                  accept=".txt"
                  className="text-xs text-muted"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleSummaryFile(file);
                  }}
                />
              </div>
              {summaryBuffer && (
                <div className="mt-3 rounded-xl border border-border/60 bg-background/60 p-3 text-sm text-muted">
                  <p className="text-[12px] uppercase tracking-wide text-muted">Texto listo para resumir</p>
                  <p className="text-foreground line-clamp-3">{summaryBuffer.slice(0, 500)}...</p>
                  {summaryFileName && <p className="text-[11px] text-muted">Archivo: {summaryFileName}</p>}
                </div>
              )}
              <div className="mt-3 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() =>
                    summaryBuffer.trim()
                      ? runSummary(summaryBuffer)
                      : toast.info("Pega texto o carga un .txt primero")
                  }
                  disabled={summaryLoading || actionLoading || !summaryBuffer.trim()}
                  className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-contrast transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {summaryLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                  Generar resumen
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSummaryBuffer("");
                    setSummaryFileName(null);
                  }}
                  className="text-xs text-muted underline"
                >
                  Limpiar
                </button>
              </div>
            </div>
          ) : selectedTool.id === "upload" ? (
            <div className="sticky bottom-2 mt-3 rounded-2xl border border-border/60 bg-card/90 p-4 shadow-lg text-sm text-muted">
              <div className="flex items-center gap-2 text-foreground">
                <Upload className="h-4 w-4" />
                <span>Subir documento</span>
              </div>
              <div
                className={`mt-2 flex cursor-pointer flex-col gap-2 rounded-xl border border-dashed p-3 text-xs transition ${
                  uploadDragActive ? "border-accent bg-accent/5" : "border-border/60 bg-background/60"
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setUploadDragActive(true);
                }}
                onDragLeave={() => setUploadDragActive(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setUploadDragActive(false);
                  const file = e.dataTransfer.files?.[0];
                  if (file) {
                    setUploadName(file.name);
                    runUpload(file);
                  }
                }}
                onClick={() => uploadInputRef.current?.click()}
              >
                <p className="text-foreground">Arrastra o selecciona un PDF</p>
                <p className="text-muted">Ingesta y tracking automático.</p>
                <input
                  ref={uploadInputRef}
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    setUploadName(file.name);
                    runUpload(file);
                  }}
                  disabled={uploading}
                />
              </div>
              {uploadName && <p className="text-xs text-muted">Archivo: {uploadName}</p>}
              {(uploadStatus || uploadError) && (
                <div className="mt-2 rounded-lg border border-border/60 bg-background/70 p-2 text-xs text-muted">
                  <p>{uploadStatus ?? "No se pudo iniciar la ingesta."}</p>
                  <div className="mt-1 h-2 w-full rounded-full bg-border/50">
                    <div
                      className="h-2 rounded-full bg-accent"
                      style={{ width: `${Math.min(uploadProgress, 100)}%` }}
                    />
                  </div>
                  {uploadDocIds.length > 0 && <p className="mt-1">Doc IDs: {uploadDocIds.join(", ")}</p>}
                  {uploadError && <p className="mt-1 text-danger">Error: {uploadError}</p>}
                  <button
                    className="mt-2 text-foreground underline"
                    onClick={resetUpload}
                    type="button"
                    disabled={uploading}
                  >
                    Limpiar
                  </button>
                </div>
              )}
            </div>
          ) : (
            <form
              className="sticky bottom-2 mt-3 flex items-end gap-3 rounded-2xl border border-border/60 bg-card/90 p-3 shadow-lg"
              onSubmit={onSend}
            >
              <div className="flex-1">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={SEARCH_PLACEHOLDER}
                  rows={2}
                  className="w-full resize-none rounded-xl border border-border bg-background px-3 py-3 text-sm text-foreground outline-none transition focus:border-accent"
                />
                <p className="mt-1 text-[11px] text-muted">
                  Enter para enviar. Herramienta activa: {selectedTool.name} ({selectedTool.id}).
                </p>
              </div>
              <button
                type="submit"
                disabled={actionLoading || summaryLoading}
                className="flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-70"
              >
                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                Ejecutar búsqueda / Q&A
              </button>
            </form>
          )}
        </main>
      </div>
    </div>
  );
}
