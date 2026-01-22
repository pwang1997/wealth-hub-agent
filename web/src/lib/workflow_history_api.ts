const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RequestOptions = {
  method?: string;
  body?: string;
};

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
    },
    body: options.body,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Request failed (${response.status}): ${text || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export type WorkflowStatus = "running" | "completed" | "failed" | "partial";
export type StepStatus = "pending" | "running" | "completed" | "skipped" | "failed";

export type WorkflowStepResult = {
  step_name?: string;
  status?: StepStatus | WorkflowStatus;
  output?: unknown;
  warnings?: string[];
  duration_ms?: number;
  llm_usage?: unknown[];
};

export type WorkflowRunSummary = {
  workflow_id: string;
  ticker: string;
  completed_at?: string | null;
  status: WorkflowStatus;
};

export type WorkflowRunListResponse = {
  runs: WorkflowRunSummary[];
  next_cursor?: string | null;
};

export type WorkflowRunRecord = {
  workflow_id: string;
  ticker: string;
  started_at: string;
  completed_at?: string | null;
  status: WorkflowStatus;
  results: Record<string, WorkflowStepResult>;
};

export type WorkflowEventRecord = {
  workflow_id: string;
  timestamp: string;
  event: string;
  step?: string | null;
  status?: string | null;
  payload?: unknown;
};

export type WorkflowRunEventsResponse = {
  events: WorkflowEventRecord[];
};

export async function listWorkflowRuns(params: {
  limit?: number;
  cursor?: string | null;
  ticker?: string | null;
}): Promise<WorkflowRunListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(params.limit ?? 20));

  if (params.cursor) {
    searchParams.set("cursor", params.cursor);
  }

  if (params.ticker) {
    searchParams.set("ticker", params.ticker);
  }

  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";

  return requestJson<WorkflowRunListResponse>(`/v1/workflow/runs${suffix}`);
}

export async function getWorkflowRun(workflowId: string): Promise<WorkflowRunRecord> {
  return requestJson<WorkflowRunRecord>(`/v1/workflow/runs/${workflowId}`);
}

export async function getWorkflowEvents(workflowId: string): Promise<WorkflowRunEventsResponse> {
  return requestJson<WorkflowRunEventsResponse>(`/v1/workflow/runs/${workflowId}/events`);
}
