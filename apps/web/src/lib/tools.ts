export type ToolStatus = "ready" | "coming-soon";

export type Tool = {
  id: string;
  name: string;
  category: string;
  description: string;
  status: ToolStatus;
  pingPath: string;
  cta?: string;
};

export const TOOLS: Tool[] = [
  {
    id: "search",
    name: "Búsqueda y recuperación",
    category: "Investigación",
    description: "Búsqueda vectorial sobre leyes públicas y documentos del despacho con filtros y metadatos.",
    status: "ready",
    pingPath: "/health?tool=search",
    cta: "Abrir búsqueda",
  },
  {
    id: "qa",
    name: "Q&A con citas",
    category: "Investigación",
    description: "Haz preguntas y recibe respuestas fundamentadas con citas al texto origen.",
    status: "ready",
    pingPath: "/health?tool=qa",
    cta: "Iniciar pregunta",
  },
  {
    id: "upload",
    name: "Carga de documentos",
    category: "Ingesta",
    description: "Sube PDFs para ingestarlos y dejarlos listos para búsqueda vectorial.",
    status: "coming-soon",
    pingPath: "/health?tool=upload",
  },
  {
    id: "summary-single",
    name: "Resumen de un documento",
    category: "Síntesis",
    description: "Destila un documento en un breve, nota al cliente o memo interno.",
    status: "coming-soon",
    pingPath: "/summary/document",
  },
  {
    id: "summary-multi",
    name: "Resumen multi-documento",
    category: "Síntesis",
    description: "Combina múltiples fuentes en una narrativa única con citas.",
    status: "coming-soon",
    pingPath: "/summary/multi",
  },
  {
    id: "drafting",
    name: "Asistente de redacción",
    category: "Redacción",
    description: "Genera borradores desde plantillas y hechos; edita antes de exportar.",
    status: "coming-soon",
    pingPath: "/draft",
  },
  {
    id: "case-builder",
    name: "Case Builder",
    category: "Inteligencia de casos",
    description: "Extracción estructurada (partes, pretensiones, línea de tiempo) con workspace editable.",
    status: "coming-soon",
    pingPath: "/cases",
  },
  {
    id: "contract-analyzer",
    name: "Analizador de contratos",
    category: "Riesgo",
    description: "Segmenta cláusulas, busca similitudes y aplica heurísticas de riesgo.",
    status: "coming-soon",
    pingPath: "/contracts/analyzer",
  },
  {
    id: "personalization",
    name: "Personalización",
    category: "Experiencia",
    description: "Perfiles de estilo y preferencias para guiar prompts y respuestas.",
    status: "coming-soon",
    pingPath: "/personalization",
  },
  {
    id: "predictive",
    name: "Analítica predictiva",
    category: "Insights",
    description: "Modela resultados y tiempos, con explicabilidad.",
    status: "coming-soon",
    pingPath: "/predictive",
  },
];
