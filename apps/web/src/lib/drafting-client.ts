import { authFetch } from "./auth-fetch";
import { API_BASE_URL } from "./config";

export type DraftRequirement = { label: string; value: string };

export type DraftRequest = {
  doc_type: string;
  objective?: string;
  audience?: string;
  tone?: string;
  language?: string;
  context?: string;
  facts?: string[];
  requirements?: DraftRequirement[];
  constraints?: string[];
  research_trace_id?: string;
  research_summary?: string;
};

export type DraftSection = { title: string; content: string };

export type DraftResponse = {
  trace_id: string;
  status: string;
  doc_type: string;
  draft: string;
  sections: DraftSection[];
  assumptions: string[];
  open_questions: string[];
  risks: string[];
  errors?: string[] | null;
};

export async function runDraft(payload: DraftRequest): Promise<DraftResponse> {
  const res = await authFetch(`${API_BASE_URL}/draft/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Draft run failed with ${res.status}`);
  }
  return (await res.json()) as DraftResponse;
}

export async function getDraft(traceId: string): Promise<DraftResponse> {
  const res = await authFetch(`${API_BASE_URL}/draft/${traceId}`, { method: "GET" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Draft fetch failed with ${res.status}`);
  }
  return (await res.json()) as DraftResponse;
}
