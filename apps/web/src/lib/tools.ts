export type ToolStatus = "ready" | "coming-soon";

export type Tool = {
  id: string;
  name: string;
  ariaLabel?: string;
  category: string;
  description: string;
  status: ToolStatus;
  pingPath: string;
  cta?: string;
};

export const TOOLS: Tool[] = [
  {
    id: "research",
    name: "Investigación",
    category: "Investigación",
    description: "Búsqueda y Q&A con citas sobre leyes públicas y docs internos.",
    status: "ready",
    pingPath: "/health?tool=search",
    cta: "Abrir búsqueda",
  },
  {
    id: "summary",
    name: "Resúmenes",
    ariaLabel: "Resumen de un documento",
    category: "Síntesis",
    description: "Resúmenes con citas para texto o documentos.",
    status: "ready",
    pingPath: "/summary/health",
    cta: "Generar resumen",
  },
  {
    id: "drafting",
    name: "Redacción",
    category: "Redacción",
    description: "Redacta desde plantillas con hechos y estilo.",
    status: "ready",
    pingPath: "/tools/health",
  },
  {
    id: "communication",
    name: "Comunicaciones",
    category: "Síntesis",
    description: "Emails/notas para clientes o internos, tono controlado.",
    status: "ready",
    pingPath: "/tools/health",
  },
  {
    id: "upload",
    name: "Carga / Organización",
    ariaLabel: "Carga de documentos",
    category: "Ingesta",
    description: "Sube PDFs para ingestarlos y taggear por matter.",
    status: "ready",
    pingPath: "/health?tool=upload",
  },
  {
    id: "review",
    name: "Revisión / Redlines",
    category: "Revisión",
    description: "Detecta riesgos y propone cláusulas alternativas.",
    status: "ready",
    pingPath: "/tools/health",
  },
  {
    id: "transcribe",
    name: "Transcribir",
    category: "Audio",
    description: "Transcribe y resume audios/llamadas con action items.",
    status: "ready",
    pingPath: "/tools/health",
  },
  {
    id: "compliance",
    name: "Compliance check",
    category: "Cumplimiento",
    description: "Evalúa documentos contra políticas/playbooks.",
    status: "ready",
    pingPath: "/tools/health",
  },
  {
    id: "tasks",
    name: "Tasks / Recordatorios",
    category: "Tareas",
    description: "Crea y gestiona tareas desde conversaciones.",
    status: "ready",
    pingPath: "/tools/health",
  },
];
