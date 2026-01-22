"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  CircleCheck,
  History,
  LayoutDashboard,
  Loader2,
  RefreshCcw,
  Search,
  TrendingUp,
} from "lucide-react";
import {
  getWorkflowEvents,
  getWorkflowRun,
  listWorkflowRuns,
  type WorkflowEventRecord,
  type WorkflowRunRecord,
  type WorkflowRunSummary,
} from "@/lib/workflow_history_api";

const stepOrder = ["retrieval", "fundamental", "news", "research", "investment"];

const statusStyles: Record<string, string> = {
  running: "border-blue-400/40 text-blue-200 bg-blue-500/20",
  completed: "border-emerald-400/40 text-emerald-200 bg-emerald-500/20",
  failed: "border-red-400/40 text-red-200 bg-red-500/20",
  partial: "border-amber-400/40 text-amber-200 bg-amber-500/20",
  pending: "border-slate-400/30 text-slate-200 bg-slate-500/10",
  skipped: "border-slate-400/30 text-slate-200 bg-slate-500/10",
};

type LoadState = "idle" | "loading" | "error";

function formatTimestamp(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return null;
  const style = statusStyles[status] || "border-white/10 text-text-muted bg-white/5";
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[0.65rem] uppercase tracking-widest ${style}`}>
      {status}
    </span>
  );
}

export default function WorkflowRunsPage() {
  const [limit, setLimit] = useState(20);
  const [tickerFilter, setTickerFilter] = useState("");
  const [runs, setRuns] = useState<WorkflowRunSummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [listState, setListState] = useState<LoadState>("idle");
  const [listError, setListError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [runRecord, setRunRecord] = useState<WorkflowRunRecord | null>(null);
  const [events, setEvents] = useState<WorkflowEventRecord[]>([]);
  const [detailState, setDetailState] = useState<LoadState>("idle");
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadRuns = useCallback(
    async ({ cursor, append = false }: { cursor?: string | null; append?: boolean } = {}) => {
      setListState("loading");
      setListError(null);
      try {
        const response = await listWorkflowRuns({
          limit,
          cursor: cursor ?? null,
          ticker: tickerFilter.trim() ? tickerFilter.trim() : null,
        });
        setNextCursor(response.next_cursor ?? null);
        setRuns((prev) => (append ? [...prev, ...response.runs] : response.runs));
        if (!append) {
          setSelectedId(null);
          setRunRecord(null);
          setEvents([]);
        }
        setListState("idle");
      } catch (error) {
        setListState("error");
        setListError(error instanceof Error ? error.message : "Unable to load workflow runs.");
      }
    },
    [limit, tickerFilter]
  );

  const loadRunDetails = useCallback(async (workflowId: string) => {
    setDetailState("loading");
    setDetailError(null);
    try {
      const [record, eventsResponse] = await Promise.all([
        getWorkflowRun(workflowId),
        getWorkflowEvents(workflowId),
      ]);
      setRunRecord(record);
      setEvents(eventsResponse.events || []);
      setDetailState("idle");
    } catch (error) {
      setDetailState("error");
      setDetailError(error instanceof Error ? error.message : "Unable to load workflow details.");
    }
  }, []);

  useEffect(() => {
    loadRuns({ cursor: null, append: false });
  }, [loadRuns]);

  useEffect(() => {
    if (selectedId || runs.length === 0) return;
    const firstId = runs[0].workflow_id;
    setSelectedId(firstId);
    loadRunDetails(firstId);
  }, [runs, selectedId, loadRunDetails]);

  const orderedEvents = useMemo(() => {
    return [...events].sort((a, b) => {
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
  }, [events]);

  const stepResults = useMemo(() => {
    if (!runRecord) return [];
    const results = runRecord.results || {};
    return stepOrder
      .filter((step) => results[step])
      .map((step) => ({ step, ...(results[step] || {}) }));
  }, [runRecord]);

  return (
    <div className="flex min-h-screen">
      <aside className="glass-panel w-[280px] m-4 flex flex-col">
        <div className="p-8 flex items-center gap-4">
          <div className="w-10 h-10 bg-accent-primary rounded-sm flex items-center justify-center text-black">
            <TrendingUp size={24} />
          </div>
          <h1 className="text-xl font-bold tracking-tight">Wealth Hub</h1>
        </div>

        <nav className="px-4 flex-1">
          {[
            { icon: <LayoutDashboard size={20} />, label: "Dashboard", href: "/", active: false },
            { icon: <History size={20} />, label: "Workflow Runs", href: "/workflows", active: true },
          ].map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className={`glass-card p-3 mb-2 flex items-center gap-3 cursor-pointer ${item.active ? "text-foreground" : "text-text-muted"}`}
            >
              {item.icon}
              <span className="font-medium text-sm">{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>

      <main className="flex-1 overflow-y-auto px-12 py-8">
        <div className="max-w-250 mx-auto w-full">
          <header className="mb-10 flex flex-wrap items-end justify-between gap-6">
            <div>
              <h2 className="text-3xl font-semibold mb-2">Workflow History</h2>
              <p className="text-text-muted text-sm">
                Browse recent workflow runs, drill into step outputs, and review event timelines.
              </p>
            </div>
            <div className="glass-card px-4 py-2 flex items-center gap-2">
              <Activity size={16} className="text-accent-secondary" />
              <span className="text-[0.7rem] uppercase tracking-widest font-bold">Live Store</span>
            </div>
          </header>

          <section className="glass-panel p-6 mb-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
              <div className="flex-1">
                <label className="text-text-muted text-[0.65rem] uppercase font-bold tracking-widest block mb-2">
                  Ticker Filter
                </label>
                <div className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-sm px-4 py-3">
                  <Search size={16} className="text-text-muted" />
                  <input
                    type="text"
                    value={tickerFilter}
                    onChange={(e) => setTickerFilter(e.target.value.toUpperCase())}
                    className="flex-1 bg-transparent text-white text-sm focus:outline-none"
                    placeholder="e.g. NVDA"
                  />
                </div>
              </div>
              <div className="w-full sm:w-40">
                <label className="text-text-muted text-[0.65rem] uppercase font-bold tracking-widest block mb-2">
                  Page Size
                </label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value) || 1)}
                  className="w-full bg-white/5 border border-white/10 rounded-sm px-4 py-3 text-white text-sm focus:outline-none focus:border-accent-primary transition-all"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  className="btn-primary flex items-center gap-2"
                  onClick={() => loadRuns({ cursor: null, append: false })}
                  disabled={listState === "loading"}
                >
                  {listState === "loading" ? <Loader2 size={16} className="animate-spin" /> : <RefreshCcw size={16} />}
                  Refresh
                </button>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(260px,360px)_1fr]">
            <div className="glass-panel p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold">Runs</h3>
                  <p className="text-xs text-text-muted">{runs.length} loaded</p>
                </div>
                {listState === "loading" && <Loader2 size={18} className="animate-spin text-accent-secondary" />}
              </div>

              {listState === "error" && (
                <div className="glass-card p-3 text-sm text-red-200 border border-red-500/30 mb-4">
                  {listError || "Unable to load workflow runs."}
                </div>
              )}

              <div className="space-y-3">
                {runs.map((run) => (
                  <button
                    key={run.workflow_id}
                    type="button"
                    className={`glass-card w-full text-left p-4 transition-all ${
                      selectedId === run.workflow_id
                        ? "border border-accent-primary/60 bg-white/6"
                        : "border border-white/5"
                    }`}
                    onClick={() => {
                      if (run.workflow_id === selectedId) return;
                      setSelectedId(run.workflow_id);
                      loadRunDetails(run.workflow_id);
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold">{run.ticker}</p>
                        <p className="text-xs text-text-muted">{run.workflow_id}</p>
                      </div>
                      <StatusBadge status={run.status} />
                    </div>
                    <p className="text-xs text-text-muted mt-3">
                      Completed: {formatTimestamp(run.completed_at)}
                    </p>
                  </button>
                ))}
              </div>

              {nextCursor && (
                <button
                  className="glass-card w-full mt-4 py-2 text-xs uppercase tracking-widest text-text-muted"
                  onClick={() => loadRuns({ cursor: nextCursor, append: true })}
                  disabled={listState === "loading"}
                >
                  Load more
                </button>
              )}
            </div>

            <div className="glass-panel p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-lg font-semibold">Run Details</h3>
                  <p className="text-xs text-text-muted">
                    {selectedId ? `Workflow ${selectedId}` : "Select a run to view full details."}
                  </p>
                </div>
                {detailState === "loading" && <Loader2 size={18} className="animate-spin text-accent-secondary" />}
              </div>

              {detailState === "error" && (
                <div className="glass-card p-3 text-sm text-red-200 border border-red-500/30 mb-4">
                  {detailError || "Unable to load workflow details."}
                </div>
              )}

              {!selectedId && detailState !== "loading" && (
                <div className="glass-card p-6 text-sm text-text-muted">
                  Select a workflow run to inspect its steps and events.
                </div>
              )}

              {runRecord && (
                <div className="space-y-6">
                  <div className="glass-card p-4">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <h4 className="text-base font-semibold flex items-center gap-2">
                          <CircleCheck size={16} className="text-accent-primary" />
                          {runRecord.ticker} workflow
                        </h4>
                        <p className="text-xs text-text-muted">{runRecord.workflow_id}</p>
                      </div>
                      <StatusBadge status={runRecord.status} />
                    </div>
                    <div className="mt-4 grid gap-3 text-xs text-text-muted sm:grid-cols-2">
                      <div>
                        <span className="uppercase tracking-widest block mb-1">Started</span>
                        <span className="text-foreground">{formatTimestamp(runRecord.started_at)}</span>
                      </div>
                      <div>
                        <span className="uppercase tracking-widest block mb-1">Completed</span>
                        <span className="text-foreground">{formatTimestamp(runRecord.completed_at)}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm uppercase tracking-widest text-text-muted mb-3">Step Results</h4>
                    {stepResults.length === 0 ? (
                      <div className="glass-card p-4 text-sm text-text-muted">
                        No step results recorded for this run.
                      </div>
                    ) : (
                      <div className="grid gap-4 md:grid-cols-2">
                        {stepResults.map((result, index) => (
                          <div key={`${result.step}-${index}`} className="glass-card p-4">
                            <div className="flex items-center justify-between gap-2">
                              <div>
                                <p className="text-sm font-semibold capitalize">{result.step}</p>
                                <p className="text-xs text-text-muted">
                                  Duration: {typeof result.duration_ms === "number" ? `${Math.round(result.duration_ms / 1000)}s` : "-"}
                                </p>
                              </div>
                              <StatusBadge status={result.status} />
                            </div>
                            {result.output && (
                              <pre className="mt-3 text-xs text-text-muted bg-black/30 border border-white/5 rounded-sm p-3 max-h-40 overflow-auto">
                                {JSON.stringify(result.output, null, 2)}
                              </pre>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <h4 className="text-sm uppercase tracking-widest text-text-muted mb-3">Events</h4>
                    {orderedEvents.length === 0 ? (
                      <div className="glass-card p-4 text-sm text-text-muted">
                        No event records available.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {orderedEvents.map((event, index) => (
                          <div key={`${event.workflow_id}-${event.timestamp}-${index}`} className="glass-card p-4">
                            <div className="flex flex-wrap items-center gap-2 text-xs">
                              <span className="text-text-muted">{formatTimestamp(event.timestamp)}</span>
                              <span className="text-foreground uppercase tracking-widest">{event.event}</span>
                              {event.step && <span className="text-text-muted">Step {event.step}</span>}
                              {event.status && <StatusBadge status={event.status} />}
                            </div>
                            {event.payload && (
                              <details className="mt-3 text-xs text-text-muted">
                                <summary className="cursor-pointer">Payload</summary>
                                <pre className="mt-2 text-xs text-text-muted bg-black/30 border border-white/5 rounded-sm p-3 max-h-40 overflow-auto">
                                  {JSON.stringify(event.payload, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
