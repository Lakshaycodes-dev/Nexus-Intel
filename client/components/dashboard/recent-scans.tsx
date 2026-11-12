"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";

import { getAnalysis, type AnalysisRecord, type AnalysisStatus } from "@/lib/api";
import {
  ANALYSIS_COMPLETE_EVENT,
  readRecentAnalyses,
} from "@/lib/recent";
import { cn } from "@/lib/utils";

const statusStyle: Record<AnalysisStatus, string> = {
  queued: "border-slate-200 bg-slate-50 text-slate-500",
  running: "border-indigo-100 bg-indigo-50 text-indigo-600",
  completed: "border-emerald-100 bg-emerald-50 text-emerald-700",
  failed: "border-rose-100 bg-rose-50 text-rose-600",
};

function StatusIcon({ status }: { status: AnalysisStatus }) {
  if (status === "completed") return <CheckCircle2 className="h-3 w-3" />;
  if (status === "failed") return <XCircle className="h-3 w-3" />;
  return <Loader2 className={cn("h-3 w-3", status === "running" && "animate-spin")} />;
}

export function RecentScans() {
  const [records, setRecords] = useState<AnalysisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const entries = readRecentAnalyses();
    if (entries.length === 0) {
      setRecords([]);
      setVisible(false);
      setLoading(false);
      setError(null);
      return;
    }

    setVisible(true);
    setLoading(true);
    setError(null);

    const results = await Promise.allSettled(
      entries.map((entry) => getAnalysis(entry.analysis_id)),
    );
    const next = results.flatMap((result) =>
      result.status === "fulfilled" ? [result.value] : [],
    );

    setRecords(next);
    setLoading(false);
    if (next.length === 0) {
      setError("Recent runs could not be loaded from the backend.");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(load, 0);
    const handler = () => load();
    window.addEventListener(ANALYSIS_COMPLETE_EVENT, handler);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener(ANALYSIS_COMPLETE_EVENT, handler);
    };
  }, [load]);

  if (!visible) return null;

  return (
    <section className="mt-5 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[14px] font-semibold tracking-tight text-ink">
              Recent live runs
            </h2>
            <span className="flex items-center gap-1 rounded-full border border-emerald-100 bg-emerald-50 px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.1em] text-emerald-700">
              <span className="h-1 w-1 animate-pulse-soft rounded-full bg-emerald-500" />
              API
            </span>
          </div>
          <p className="mt-1 text-[10px] text-slate-400">
            Persisted analyses fetched from GET /api/v1/analyze/&#123;id&#125;
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          aria-label="Refresh recent runs"
          className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 text-slate-400 transition hover:text-slate-700"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
        </button>
      </div>

      {records.length > 0 ? (
        <div className="divide-y divide-slate-100">
          {records.map((record) => (
            <Link
              key={record.analysis_id}
              href={`/dashboard/competitors/${encodeURIComponent(record.domain)}`}
              className="group flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-slate-50/70"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-indigo-100 bg-indigo-50 text-indigo-600">
                <Activity className="h-3 w-3" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[11.5px] font-medium text-slate-700">
                  {record.domain}
                </p>
                <p className="mt-0.5 truncate font-mono text-[8.5px] text-slate-400">
                  {record.analysis_id} ·{" "}
                  {record.execution_time_sec !== null
                    ? `${record.execution_time_sec.toFixed(1)}s`
                    : "—"}{" "}
                  · {new Date(record.created_at).toLocaleString()}
                </p>
              </div>
              <span
                className={cn(
                  "flex items-center gap-1 rounded-full border px-2 py-1 text-[8px] font-semibold uppercase tracking-[0.08em]",
                  statusStyle[record.status],
                )}
              >
                <StatusIcon status={record.status} />
                {record.status}
              </span>
              <ArrowUpRight className="h-3 w-3 shrink-0 text-slate-300 transition group-hover:text-indigo-500" />
            </Link>
          ))}
        </div>
      ) : (
        <div className="px-5 py-6 text-center">
          <p className="text-[11px] font-medium text-slate-600">
            {loading ? "Loading recent runs…" : error}
          </p>
          {!loading && error ? (
            <p className="mt-1 text-[9px] text-slate-400">
              Check that the FastAPI backend and MongoDB are running.
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}
