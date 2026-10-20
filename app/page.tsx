"use client";

import { useState } from "react";
import {
  Check,
  Database,
  Download,
  Newspaper,
  Radar,
  RotateCw,
  ShieldCheck,
  Sparkles,
  Tags,
  Timer,
  Zap,
} from "lucide-react";
import AgentExecutionStepper, {
  STEP_DEFINITIONS,
} from "@/components/AgentExecutionStepper";
import ComparisonMatrix from "@/components/ComparisonMatrix";
import CompetitorInputForm from "@/components/CompetitorInputForm";
import MetricsOverview from "@/components/MetricsOverview";
import Navbar from "@/components/Navbar";
import OffsiteIntelligence from "@/components/OffsiteIntelligence";
import {
  analyzeCompetitor,
  DEFAULT_ANALYSIS_OPTIONS,
  USE_MOCK_DATA,
  type AnalysisOptions,
  type StepProgressHandler,
  type StepStatus,
} from "@/lib/api";
import {
  getCompanyName,
  getMockCompetitorData,
  type CompetitorData,
} from "@/lib/mockData";

const EMPTY_STEPS: StepStatus[] = STEP_DEFINITIONS.map(() => "pending");

const PREVIEW_DATA = USE_MOCK_DATA ? getMockCompetitorData("stripe.com") : null;

export default function DashboardPage() {
  const [data, setData] = useState<CompetitorData | null>(PREVIEW_DATA);
  const [steps, setSteps] = useState<StepStatus[]>(EMPTY_STEPS);
  const [isRunning, setIsRunning] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [isSample, setIsSample] = useState(Boolean(PREVIEW_DATA));
  const [error, setError] = useState<string | null>(null);
  const [targetDomain, setTargetDomain] = useState(
    PREVIEW_DATA?.domain ?? "stripe.com",
  );

  const traceVisible = hasStarted || isRunning;

  async function handleAnalyze(domain: string, options: AnalysisOptions) {
    setIsRunning(true);
    setHasStarted(true);
    setError(null);
    setTargetDomain(domain);
    setSteps([...EMPTY_STEPS]);

    const onProgress: StepProgressHandler = (index, status) => {
      setSteps((previous) => {
        const next = [...previous];
        next[index] = status;
        return next;
      });
    };

    try {
      const result = await analyzeCompetitor(domain, options, onProgress);
      setData(result);
      setIsSample(false);
    } catch (analysisError) {
      setSteps((previous) =>
        previous.map((status) => (status === "active" ? "error" : status)),
      );
      setError(
        analysisError instanceof Error
          ? analysisError.message
          : "The autonomous analysis run failed. Please try again.",
      );
    } finally {
      setIsRunning(false);
    }
  }

  function handleExport() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `nexus-intel-${data.domain}-${new Date()
      .toISOString()
      .slice(0, 10)}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="relative min-h-screen">
      <Navbar />

      <div className="pointer-events-none absolute inset-x-0 top-0 h-[560px] grid-overlay" />
      <div className="pointer-events-none absolute left-1/2 top-[-180px] h-[420px] w-[720px] -translate-x-1/2 rounded-full bg-indigo-600/15 blur-[120px]" />

      <main className="relative mx-auto max-w-7xl px-4 pb-16 pt-10 sm:px-6 sm:pt-14 lg:px-8">
        <section className="grid gap-10 pb-10 lg:grid-cols-12 lg:items-center lg:gap-8">
          <div className="lg:col-span-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-400/20 bg-indigo-500/[0.07] px-3 py-1">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-70" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-indigo-400" />
              </span>
              <span className="text-[10.5px] font-medium uppercase tracking-[0.16em] text-indigo-200/90">
                Autonomous market intelligence
              </span>
            </div>

            <h1 className="mt-5 text-balance text-4xl font-semibold leading-[1.06] tracking-[-0.03em] text-white sm:text-5xl">
              Know the market{" "}
              <span className="text-gradient-accent">before it moves.</span>
            </h1>

            <p className="mt-4 max-w-xl text-balance text-[13.5px] leading-relaxed text-slate-400 sm:text-sm">
              Nexus Intel deploys a five-stage agent to uncover competitor
              pricing, hidden feature toggles, and off-site sentiment — then
              returns schema-perfect intelligence in about 30 seconds.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2">
              {[
                "5-stage autonomous pipeline",
                "Schema-validated output",
                "~480× analyst leverage",
              ].map((item) => (
                <span
                  key={item}
                  className="flex items-center gap-1.5 text-[11px] text-slate-400"
                >
                  <span className="flex h-4 w-4 items-center justify-center rounded-full border border-emerald-400/25 bg-emerald-400/[0.08]">
                    <Check className="h-2.5 w-2.5 text-emerald-400" strokeWidth={3} />
                  </span>
                  {item}
                </span>
              ))}
            </div>

            <div className="mt-7 flex flex-wrap items-center gap-2">
              <span className="chip">
                <Zap className="h-3 w-3 text-amber-300/80" />
                4 hrs → 30 sec
              </span>
              <span className="chip">
                <ShieldCheck className="h-3 w-3 text-emerald-300/80" />
                Pydantic-validated JSON
              </span>
              <span className="chip">
                <Database className="h-3 w-3 text-cyan-300/80" />
                MongoDB snapshots
              </span>
            </div>
          </div>

          <div className="lg:col-span-6">
            <CompetitorInputForm
              onSubmit={handleAnalyze}
              isLoading={isRunning}
              defaultDomain={targetDomain}
            />
          </div>
        </section>

        <div className="space-y-6">
          {traceVisible && (
            <AgentExecutionStepper
              steps={steps}
              isRunning={isRunning}
              domain={targetDomain}
              executionTimeSec={!isRunning && data ? data.executionTimeSec : null}
            />
          )}

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-xl border border-rose-400/25 bg-rose-500/[0.07] px-4 py-3"
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-rose-400/30 bg-rose-500/15 text-[10px] font-bold text-rose-300">
                !
              </span>
              <div>
                <p className="text-[12px] font-medium text-rose-200">
                  Analysis run failed
                </p>
                <p className="mt-0.5 text-[11px] leading-relaxed text-rose-200/60">
                  {error}
                </p>
              </div>
            </div>
          )}

          <MetricsOverview />

          {data ? (
            <section aria-labelledby="snapshot-heading" className="space-y-4">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-indigo-300/70">
                    Intelligence snapshot
                  </p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-indigo-400/25 bg-gradient-to-br from-indigo-500/25 to-cyan-400/10 text-[13px] font-semibold text-indigo-200">
                      {getCompanyName(data.domain).charAt(0)}
                    </span>
                    <h2
                      id="snapshot-heading"
                      className="text-xl font-semibold tracking-tight text-white"
                    >
                      {getCompanyName(data.domain)}
                    </h2>
                    <span className="chip font-mono text-slate-400">
                      {data.domain}
                    </span>
                    {isSample && (
                      <span className="chip border-amber-400/25 bg-amber-400/[0.08] text-amber-300">
                        Preview snapshot
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 text-[11.5px] text-slate-500">
                    {isSample
                      ? "Sample intelligence loaded. Launch a run to replace it with live data."
                      : "Generated by the autonomous pipeline · schema-validated · immutable snapshot stored."}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      handleAnalyze(data.domain, DEFAULT_ANALYSIS_OPTIONS)
                    }
                    disabled={isRunning}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11px] font-medium text-slate-300 transition hover:border-indigo-400/30 hover:bg-indigo-500/10 hover:text-white focus-ring disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <RotateCw
                      className={`h-3.5 w-3.5 ${isRunning ? "animate-spin" : ""}`}
                    />
                    Re-run
                  </button>
                  <button
                    type="button"
                    onClick={handleExport}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-400/25 bg-indigo-500/[0.1] px-3 py-1.5 text-[11px] font-medium text-indigo-200 transition hover:bg-indigo-500/[0.18] hover:text-white focus-ring"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Export JSON
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.06] sm:grid-cols-4">
                {[
                  {
                    label: "Pricing tiers",
                    value: `${data.pricing.length}`,
                    detail: "captured",
                    icon: Tags,
                  },
                  {
                    label: "Off-site signals",
                    value: `${data.offsiteNews.length}`,
                    detail: "indexed",
                    icon: Newspaper,
                  },
                  {
                    label: "Execution",
                    value: `${data.executionTimeSec.toFixed(1)}s`,
                    detail: "agent runtime",
                    icon: Timer,
                  },
                  {
                    label: "Snapshot",
                    value: "MongoDB",
                    detail: "Atlas · persisted",
                    icon: Database,
                  },
                ].map((stat) => {
                  const Icon = stat.icon;
                  return (
                    <div
                      key={stat.label}
                      className="flex items-center gap-2.5 bg-ink-900/80 px-4 py-3"
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                      <div className="min-w-0">
                        <p className="truncate text-[9.5px] uppercase tracking-[0.12em] text-slate-600">
                          {stat.label}
                        </p>
                        <p className="mt-0.5 truncate text-[12.5px] font-semibold text-slate-200">
                          {stat.value}
                          <span className="ml-1 text-[9.5px] font-normal text-slate-500">
                            {stat.detail}
                          </span>
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div
                className={`grid gap-4 transition-opacity duration-300 xl:grid-cols-5 ${
                  isRunning ? "pointer-events-none opacity-45" : "opacity-100"
                }`}
                aria-busy={isRunning}
              >
                <div className="xl:col-span-3">
                  <ComparisonMatrix data={data} />
                </div>
                <div className="xl:col-span-2">
                  <OffsiteIntelligence data={data} />
                </div>
              </div>
            </section>
          ) : (
            <section className="glass-panel flex flex-col items-center justify-center px-6 py-16 text-center">
              <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-400/25 bg-indigo-500/10">
                <Radar className="h-6 w-6 text-indigo-300" />
                <span className="absolute inset-0 animate-pulse-ring rounded-2xl border border-indigo-400/30" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-white">
                No snapshot on record
              </h2>
              <p className="mt-1.5 max-w-md text-[12px] leading-relaxed text-slate-400">
                Launch an autonomous run to discover competitor pricing, hidden
                feature accordions, and off-site sentiment.
              </p>
              <button
                type="button"
                onClick={() =>
                  handleAnalyze("stripe.com", DEFAULT_ANALYSIS_OPTIONS)
                }
                className="mt-5 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-sky-500 px-4 py-2 text-[12px] font-semibold text-white shadow-glow-sm transition hover:brightness-110 focus-ring"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Try a sample run
              </button>
            </section>
          )}
        </div>
      </main>

      <footer className="relative border-t border-white/[0.06]">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-6 text-center sm:flex-row sm:px-6 sm:text-left lg:px-8">
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-cyan-400">
              <Radar className="h-3 w-3 text-white" />
            </div>
            <span className="text-[11px] font-medium text-slate-400">
              Nexus Intel
            </span>
            <span className="text-slate-700">·</span>
            <span className="text-[10.5px] text-slate-600">
              Built for KriticalHacks 2026
            </span>
          </div>
          <p className="flex items-center gap-1.5 text-[10px] text-slate-600">
            <span className="h-1 w-1 rounded-full bg-emerald-400/70" />
            TinyFish · Gemini 1.5 Flash · MongoDB Atlas
          </p>
        </div>
      </footer>
    </div>
  );
}
