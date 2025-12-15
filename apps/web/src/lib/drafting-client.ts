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

export type DraftEvent =
  | { type: "start"; trace_id: string; status: string }
  | { type: "update"; trace_id: string; status?: string; data: Partial<DraftResponse> }
  | ({ type: "done"; trace_id: string } & DraftResponse)
  | { type: "error"; trace_id: string; error: string; status?: string };

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

export function streamDraft(
  payload: DraftRequest,
  opts: {
    onEvent: (evt: DraftEvent) => void;
    onError?: (err: Error) => void;
    signal?: AbortSignal;
  }
) {
  const controller = new AbortController();
  const signal = opts.signal || controller.signal;

  const start = async () => {
    const res = await authFetch(`${API_BASE_URL}/draft/run/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
    if (!res.ok || !res.body) {
      const text = await res.text();
      const err = new Error(text || `Draft stream failed with ${res.status}`);
      opts.onError?.(err);
      throw err;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
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
            const evt = JSON.parse(trimmed) as DraftEvent;
            opts.onEvent(evt);
          } catch (err) {
            console.error("Failed to parse draft stream event", err);
            opts.onError?.(err as Error);
          }
        }
      }
    } catch (err) {
      opts.onError?.(err as Error);
      throw err;
    }
  };

  return {
    controller,
    start,
    cancel: () => controller.abort(),
  };
}
