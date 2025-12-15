import { authFetch } from "./auth-fetch";
import { API_BASE_URL } from "./config";

export type ReviewSection = { title?: string; content?: string };

export type ReviewRequest = {
  doc_type: string;
  objective?: string;
  audience?: string;
  guidelines?: string;
  jurisdiction?: string;
  constraints?: string[];
  text?: string;
  sections?: ReviewSection[];
  research_trace_id?: string;
  research_summary?: string;
};

export type ReviewFinding = { section?: string; issue: string; severity: string };
export type ReviewIssue = { category: string; description: string; severity: string; section?: string; priority?: string };
export type ReviewSuggestion = { section?: string; suggestion: string; rationale?: string };

export type ReviewResponse = {
  trace_id: string;
  status: string;
  doc_type: string;
  structural_findings: ReviewFinding[];
  issues: ReviewIssue[];
  suggestions: ReviewSuggestion[];
  qa_notes: string[];
  residual_risks: string[];
  summary?: Record<string, unknown> | null;
  conflict_check?: Record<string, unknown> | null;
  errors?: string[] | null;
};

export type ReviewEvent =
  | { type: "start"; trace_id: string; status: string }
  | { type: "update"; trace_id: string; status?: string; data: Partial<ReviewResponse> }
  | ({ type: "done"; trace_id: string } & ReviewResponse)
  | { type: "error"; trace_id: string; error: string; status?: string };

export async function runReview(payload: ReviewRequest): Promise<ReviewResponse> {
  const res = await authFetch(`${API_BASE_URL}/review/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Review run failed with ${res.status}`);
  }
  return (await res.json()) as ReviewResponse;
}

export async function getReview(traceId: string): Promise<ReviewResponse> {
  const res = await authFetch(`${API_BASE_URL}/review/${traceId}`, { method: "GET" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Review fetch failed with ${res.status}`);
  }
  return (await res.json()) as ReviewResponse;
}

export function streamReview(
  payload: ReviewRequest,
  opts: { onEvent: (evt: ReviewEvent) => void; onError?: (err: Error) => void; signal?: AbortSignal }
) {
  const controller = new AbortController();
  const signal = opts.signal || controller.signal;

  const start = async () => {
    const res = await authFetch(`${API_BASE_URL}/review/run/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
    if (!res.ok || !res.body) {
      const text = await res.text();
      const err = new Error(text || `Review stream failed with ${res.status}`);
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
            const evt = JSON.parse(trimmed) as ReviewEvent;
            opts.onEvent(evt);
          } catch (err) {
            console.error("Failed to parse review stream event", err);
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
