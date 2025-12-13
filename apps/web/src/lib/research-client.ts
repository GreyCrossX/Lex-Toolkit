import { authFetch } from "./auth-fetch";
import { API_BASE_URL } from "./config";

export type ResearchIssue = {
  id: string;
  question: string;
  priority?: string;
  area?: string;
  status?: string;
};

export type ResearchStep = {
  id: string;
  issue_id?: string;
  layer?: string;
  description?: string;
  status?: string;
  query_ids?: string[];
  top_k?: number;
};

export type ResearchQueryResult = {
  doc_id?: string;
  title?: string;
  citation?: string;
  snippet?: string;
  score?: number;
  norm_layer?: string;
};

export type ResearchQuery = {
  id: string;
  issue_id?: string;
  layer?: string;
  query?: string;
  filters?: Record<string, string>;
  top_k?: number;
  results?: ResearchQueryResult[];
};

export type ResearchBriefing = {
  overview?: string;
  legal_characterization?: string;
  recommended_strategy?: string;
  issue_answers?: Record<string, unknown>[];
  open_questions?: string[];
};

export type ConflictHit = {
  name?: string;
  doc_id?: string;
  chunk_id?: string;
  distance?: number | string;
  source?: string;
  links?: unknown;
};

export type ConflictCheck = {
  opposing_parties?: string[];
  conflict_found?: boolean;
  reason?: string;
  hits?: ConflictHit[];
};

export type ResearchRunResponse = {
  trace_id: string;
  status: string;
  issues: ResearchIssue[];
  research_plan: ResearchStep[];
  queries: ResearchQuery[];
  briefing?: ResearchBriefing | null;
  conflict_check?: ConflictCheck | null;
  errors?: string[] | null;
};

export type ResearchEvent =
  | { type: "start"; trace_id: string; status: string }
  | { type: "update"; trace_id: string; status?: string; data: Partial<ResearchRunResponse> }
  | ({ type: "done"; trace_id: string } & ResearchRunResponse)
  | { type: "keepalive"; trace_id: string; status?: string }
  | { type: "error"; trace_id: string; error: string; status?: string };

export async function runResearch(
  prompt: string,
  opts: { maxSteps?: number; traceId?: string } = {}
): Promise<ResearchRunResponse> {
  const res = await authFetch(`${API_BASE_URL}/research/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      max_search_steps: opts.maxSteps,
      trace_id: opts.traceId,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Research run failed with ${res.status}`);
  }
  return (await res.json()) as ResearchRunResponse;
}

export async function getResearchRun(traceId: string): Promise<ResearchRunResponse> {
  const res = await authFetch(`${API_BASE_URL}/research/${traceId}`, { method: "GET" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Research fetch failed with ${res.status}`);
  }
  return (await res.json()) as ResearchRunResponse;
}

export function streamResearch(
  prompt: string,
  opts: {
    maxSteps?: number;
    traceId?: string;
    onEvent: (evt: ResearchEvent) => void;
    onError?: (err: Error) => void;
    signal?: AbortSignal;
  }
) {
  const controller = new AbortController();
  const signal = opts.signal || controller.signal;

  const start = async () => {
    const res = await authFetch(`${API_BASE_URL}/research/run/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        max_search_steps: opts.maxSteps,
        trace_id: opts.traceId,
      }),
      signal,
    });
    if (!res.ok || !res.body) {
      const text = await res.text();
      const err = new Error(text || `Research stream failed with ${res.status}`);
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
            const evt = JSON.parse(trimmed) as ResearchEvent;
            opts.onEvent(evt);
          } catch (err) {
            console.error("Failed to parse research stream event", err);
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
