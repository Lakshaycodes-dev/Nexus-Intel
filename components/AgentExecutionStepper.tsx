"use client";

import {
  Bot,
  BrainCircuit,
  Check,
  Database,
  FileCode2,
  Search,
  Timer,
  X,
} from "lucide-react";
import type { StepStatus } from "@/lib/api";

export const STEP_DEFINITIONS = [
  {
    title: "TinyFish Search API",
    description: "Discovering URLs & press",
    detail: "Crawling search results, newsrooms and community threads.",
    icon: Search,
    accent: "text-sky-300",
  },
  {
    title: "TinyFish Web Agent",
    description: "Interacting with dynamic DOM & toggles",
    detail: "Clicking pricing toggles and expanding hidden accordions.",
    icon: Bot,
    accent: "text-indigo-300",
  },
  {
    title: "TinyFish Fetch API",
    description: "Stripping JS bloat to clean Markdown",
    detail: "Removing scripts and navigation for token-dense context.",
    icon: FileCode2,
    accent: "text-cyan-300",
  },
  {
    title: "Gemini 1.5 Flash",
    description: "Structuring JSON schema",
    detail: "Constraining output to a deterministic Pydantic contract.",
    icon: BrainCircuit,
    accent: "text-violet-300",
  },
  {
    title: "MongoDB Atlas",
    description: "Persisting snapshot",
    detail: "Writing a versioned competitor snapshot for trend analysis.",
    icon: Database,
    accent: "text-emerald-300",
  },
] as const;

const STATUS_LABEL: Record<StepStatus, string> = {
  pending: "Queued",
  active: "Running",
  complete: "Complete",
  error: "Failed",
};

const STATUS_STYLE: Record<StepStatus, string> = {
  pending: "border-white/10 bg-white/[0.03] text-slate-500",
  active: "border-indigo-400/60 bg-indigo-500/15 text-indigo-200 shadow-glow-sm",
  complete: "border-emerald-400/35 bg-emerald-500/10 text-emerald-300",
  error: "border-rose-400/45 bg-rose-500/10 text-rose-300",
};

const STATUS_CHIP: Record<StepStatus, string> = {
  pending: "border-white/[0.07] bg-white/[0.02] text-slate-600",
  active: "border-indigo-400/25 bg-indigo-500/10 text-indigo-300",
  complete: "border-emerald-400/20 bg-emerald-500/[0.08] text-emerald-300/90",
  error: "border-rose-400/25 bg-rose-500/10 text-rose-300",
};

interface AgentExecutionStepperProps {
  steps: StepStatus[];
  isRunning: boolean;
  domain?: string;
  executionTimeSec?: number | null;
}

function statusOf(steps: StepStatus[], index: number): StepStatus {
  return steps[index] ?? "pending";
}

function StepNode({
  index,
  status,
  compact = false,
}: {
  index: number;
  status: StepStatus;
  compact?: boolean;
}) {
  const step = STEP_DEFINITIONS[index];
  const Icon = step.icon;
  const complete = status === "complete";

  return (
    <div className="relative">
      <div
        className={`relative flex items-center justify-center rounded-2xl border transition-all duration-500 ${STATUS_STYLE[status]} ${
          compact ? "h-10 w-10" : "h-14 w-14"
        }`}
      >
        {status === "active" && (
          <span className="absolute inset-0 animate-pulse-ring rounded-2xl border border-indigo-400/50" />
        )}
        <Icon
          className={`${compact ? "h-4 w-4" : "h-5 w-5"} ${
            status === "pending" ? "opacity-60" : ""
          }`}
          strokeWidth={1.9}
        />

        <span
          className={`absolute -right-1.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full border font-mono text-[9px] ${
            complete
              ? "border-emerald-400/50 bg-emerald-400 text-emerald-950"
              : status === "error"
                ? "border-rose-400/50 bg-rose-500 text-white"
                : "border-white/10 bg-ink-900 text-slate-500"
          }`}
        >
          {complete ? (
            <Check className="h-2.5 w-2.5" strokeWidth={3.5} />
          ) : status === "error" ? (
            <X className="h-2.5 w-2.5" strokeWidth={3} />
          ) : (
            index + 1
          )}
        </span>
      </div>
    </div>
  );
}

export default function AgentExecutionStepper({
  steps,
  isRunning,
  domain,
  executionTimeSec,
}: AgentExecutionStepperProps) {
  const completed = steps.filter((step) => step === "complete").length;
  const activeIndex = steps.findIndex((step) => step === "active");
  const hasError = steps.some((step) => step === "error");
  const progress = Math.round(
    ((completed + (activeIndex >= 0 ? 0.5 : 0)) / STEP_DEFINITIONS.length) * 100,
  );
  const done = completed === STEP_DEFINITIONS.length;

  return (
    <section className="glass-panel relative overflow-hidden animate-fade-up" aria-live="polite">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-400/60 to-transparent" />
      <div className="pointer-events-none absolute -left-24 top-0 h-48 w-48 rounded-full bg-indigo-500/10 blur-3xl" />

      <div className="relative border-b border-white/[0.06] p-5 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-400/25 bg-indigo-500/10">
              <Bot className="h-[18px] w-[18px] text-indigo-300" />
              {isRunning && (
                <span className="absolute -right-0.5 -top-0.5 h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-400" />
                </span>
              )}
            </div>
            <div>
              <h2 className="text-[15px] font-semibold tracking-tight text-white">
                Agent execution trace
              </h2>
              <p className="text-[11px] text-slate-500">
                {domain ? (
                  <>
                    Autonomous pipeline ·{" "}
                    <span className="font-mono text-slate-400">{domain}</span>
                  </>
                ) : (
                  "Autonomous pipeline · streaming live events"
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {done && !isRunning ? (
              <span className="chip border-emerald-400/25 bg-emerald-500/[0.08] text-emerald-300">
                <Check className="h-3 w-3" /> Run complete
              </span>
            ) : hasError ? (
              <span className="chip border-rose-400/25 bg-rose-500/[0.08] text-rose-300">
                <X className="h-3 w-3" /> Run failed
              </span>
            ) : (
              <span className="chip border-indigo-400/25 bg-indigo-500/[0.08] text-indigo-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" />
                Live
              </span>
            )}
            {!isRunning && executionTimeSec ? (
              <span className="chip border-white/[0.07] font-mono text-slate-400">
                <Timer className="h-3 w-3" />
                {executionTimeSec.toFixed(1)}s
              </span>
            ) : (
              <span className="chip border-white/[0.07] font-mono text-slate-500">
                {completed}/{STEP_DEFINITIONS.length} stages
              </span>
            )}
          </div>
        </div>

        <div className="mt-4">
          <div className="mb-1.5 flex items-center justify-between text-[10px] uppercase tracking-[0.14em]">
            <span className="text-slate-600">Pipeline progress</span>
            <span className="font-mono text-indigo-300/90">{progress}%</span>
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-white/[0.06]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-sky-400 to-cyan-300 transition-all duration-700 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      <div className="px-5 py-6 sm:px-6">
        <div className="hidden md:grid md:grid-cols-5 md:gap-2">
          {STEP_DEFINITIONS.map((step, index) => {
            const status = statusOf(steps, index);
            const isLast = index === STEP_DEFINITIONS.length - 1;

            return (
              <div key={step.title} className="relative flex flex-col items-center px-1 text-center">
                {!isLast && (
                  <div className="absolute left-[calc(50%+34px)] top-7 h-px w-[calc(100%-68px)] bg-white/[0.08]">
                    <div
                      className={`h-full bg-gradient-to-r from-indigo-400/80 to-sky-400/60 transition-all duration-700 ${
                        status === "complete" ? "w-full" : "w-0"
                      }`}
                    />
                  </div>
                )}

                <StepNode index={index} status={status} />

                <div className="mt-3 min-h-[96px]">
                  <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-slate-600">
                    Step 0{index + 1}
                  </p>
                  <h3
                    className={`mt-1 text-[12.5px] font-semibold leading-tight transition-colors ${
                      status === "pending" ? "text-slate-500" : "text-slate-100"
                    }`}
                  >
                    {step.title}
                  </h3>
                  <p className="mt-1 text-[10.5px] leading-snug text-slate-500">
                    {step.description}
                  </p>
                  <span
                    className={`mt-2 inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider ${STATUS_CHIP[status]}`}
                  >
                    {status === "active" && (
                      <span className="h-1 w-1 animate-pulse rounded-full bg-indigo-400" />
                    )}
                    {STATUS_LABEL[status]}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="space-y-0 md:hidden">
          {STEP_DEFINITIONS.map((step, index) => {
            const status = statusOf(steps, index);
            const isLast = index === STEP_DEFINITIONS.length - 1;

            return (
              <div key={step.title} className="relative flex gap-3.5 pb-5 last:pb-0">
                {!isLast && (
                  <div className="absolute bottom-0 left-5 top-11 w-px bg-white/[0.08]">
                    <div
                      className={`w-full bg-gradient-to-b from-indigo-400/80 to-sky-400/60 transition-all duration-700 ${
                        status === "complete" ? "h-full" : "h-0"
                      }`}
                    />
                  </div>
                )}
                <StepNode index={index} status={status} compact />
                <div className="min-w-0 flex-1 pt-0.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-600">
                      Step 0{index + 1}
                    </p>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider ${STATUS_CHIP[status]}`}
                    >
                      {STATUS_LABEL[status]}
                    </span>
                  </div>
                  <h3
                    className={`mt-0.5 text-[12.5px] font-semibold ${
                      status === "pending" ? "text-slate-500" : "text-slate-100"
                    }`}
                  >
                    {step.title}
                  </h3>
                  <p className="text-[10.5px] text-slate-500">{step.description}</p>
                  {status === "active" && (
                    <p className="mt-1 text-[10px] leading-snug text-indigo-300/70">
                      {step.detail}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-x-2 gap-y-1.5 border-t border-white/[0.05] pt-4 text-[10px] text-slate-600">
          <span className="font-mono uppercase tracking-[0.16em] text-slate-500">
            Stack
          </span>
          <span className="h-1 w-1 rounded-full bg-slate-700" />
          <span>TinyFish Search</span>
          <span className="h-1 w-1 rounded-full bg-slate-700" />
          <span>TinyFish Web Agent</span>
          <span className="h-1 w-1 rounded-full bg-slate-700" />
          <span>TinyFish Fetch</span>
          <span className="h-1 w-1 rounded-full bg-slate-700" />
          <span>Gemini 1.5 Flash</span>
          <span className="h-1 w-1 rounded-full bg-slate-700" />
          <span>MongoDB Atlas</span>
        </div>
      </div>
    </section>
  );
}
