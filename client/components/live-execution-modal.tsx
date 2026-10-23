"use client";

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  ChevronRight,
  Circle,
  Globe2,
  Layers3,
  Loader2,
  MousePointerClick,
  Radar,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import type { ExecutionStep, ScopeKey, TerminalLine } from "@/lib/types";
import { scanScopeLabels } from "@/lib/scopes";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";

interface LiveExecutionModalProps {
  open: boolean;
  onClose: () => void;
  target: string;
  scopes: ScopeKey[];
}

const TOTAL_DURATION = 8200;

const STEPS: ExecutionStep[] = [
  {
    id: 1,
    title: "Off-site Discovery",
    shortTitle: "Discovery",
    description: "Scanning news, press, community, and review mentions.",
    startAt: 0,
    endAt: 2100,
  },
  {
    id: 2,
    title: "Autonomous Navigation",
    shortTitle: "Navigate",
    description: "Toggling annual pricing and opening hidden accordions.",
    startAt: 2100,
    endAt: 4400,
  },
  {
    id: 3,
    title: "Clean Extraction",
    shortTitle: "Extract",
    description: "Removing navigation, scripts, and duplicated DOM noise.",
    startAt: 4400,
    endAt: 6300,
  },
  {
    id: 4,
    title: "AI Structuring",
    shortTitle: "Structure",
    description: "Generating a normalized schema and executive brief.",
    startAt: 6300,
    endAt: TOTAL_DURATION,
  },
];

const STEP_ICONS = [Radar, MousePointerClick, Layers3, Sparkles];

const TERMINAL_LINES: TerminalLine[] = [
  { at: 250, time: "+0.3s", level: "muted", message: "nexus · initializing autonomous scan session" },
  { at: 650, time: "+0.7s", level: "info", message: "resolve target · normalizing public entry points" },
  { at: 1050, time: "+1.1s", level: "muted", message: "discovered 14 public surfaces · 6 off-site sources" },
  { at: 1450, time: "+1.5s", level: "info", message: "GET /pricing → 200 OK · 184 KB" },
  { at: 1800, time: "+1.8s", level: "success", message: "pricing matrix found · 3 tiers detected" },
  { at: 2250, time: "+2.3s", level: "info", message: "opening pricing accordion · 7 hidden rows revealed" },
  { at: 2700, time: "+2.7s", level: "muted", message: "toggling annual switch · recalculating tier values" },
  { at: 3150, time: "+3.2s", level: "info", message: "navigating /product/changelog → 200 OK" },
  { at: 3550, time: "+3.6s", level: "success", message: "12 product changes located · 4 launches classified" },
  { at: 3950, time: "+4.0s", level: "muted", message: "cross-referencing off-site mentions · 18 sources" },
  { at: 4450, time: "+4.5s", level: "info", message: "stripping 41 tracking scripts · 812 KB removed" },
  { at: 4850, time: "+4.9s", level: "success", message: "clean extraction complete · 96.4% signal density" },
  { at: 5300, time: "+5.3s", level: "muted", message: "normalizing pricing deltas and feature mappings" },
  { at: 5750, time: "+5.8s", level: "info", message: "building comparison matrix · 48 structured rows" },
  { at: 6250, time: "+6.3s", level: "info", message: "generating executive summary · 4 key findings" },
  { at: 6750, time: "+6.8s", level: "muted", message: "validating JSON schema · version 2.4" },
  { at: 7250, time: "+7.3s", level: "success", message: "confidence score · 96.2%" },
  { at: 7800, time: "+7.8s", level: "success", message: "intelligence brief ready · scan complete" },
];

type StepState = "pending" | "active" | "complete";

function ScanPanel({
  onClose,
  target,
  scopes,
}: Omit<LiveExecutionModalProps, "open">) {
  const [elapsed, setElapsed] = useState(0);
  const terminalRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const startedAt = Date.now();
    const interval = window.setInterval(() => {
      const next = Math.min(Date.now() - startedAt, TOTAL_DURATION);
      setElapsed(next);
      if (next >= TOTAL_DURATION) {
        window.clearInterval(interval);
      }
    }, 80);

    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusTimer = window.setTimeout(() => closeRef.current?.focus(), 350);

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previous;
      window.clearTimeout(focusTimer);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  const visibleLines = useMemo(
    () => TERMINAL_LINES.filter((line) => line.at <= elapsed),
    [elapsed],
  );

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [visibleLines.length]);

  const progress = Math.min(100, Math.round((elapsed / TOTAL_DURATION) * 100));
  const complete = elapsed >= TOTAL_DURATION;
  const activeIndex = complete
    ? STEPS.length
    : STEPS.findIndex((step) => elapsed >= step.startAt && elapsed < step.endAt);

  function stateFor(index: number): StepState {
    if (complete || elapsed >= STEPS[index].endAt) return "complete";
    if (index === activeIndex) return "active";
    return "pending";
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-[80]"
    >
          <motion.button
            type="button"
            aria-label="Close live scan panel"
            className="absolute inset-0 h-full w-full cursor-default bg-slate-950/30 backdrop-blur-[3px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            tabIndex={-1}
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="live-scan-title"
            className="absolute right-0 top-0 flex h-full w-full max-w-[600px] flex-col border-l border-slate-200 bg-[#FBFCFE] shadow-2xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
          >
            <div className="relative overflow-hidden border-b border-slate-200/80 bg-white px-5 pb-5 pt-5 sm:px-7">
              <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-indigo-100/60 blur-3xl" />
              <div className="relative flex items-start justify-between gap-4">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <span
                      className={cn(
                        "flex h-6 items-center gap-1.5 rounded-full border px-2 text-[10px] font-semibold uppercase tracking-[0.16em]",
                        complete
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                          : "border-indigo-100 bg-indigo-50 text-indigo-700",
                      )}
                    >
                      <span
                        className={cn(
                          "h-1.5 w-1.5 rounded-full",
                          complete ? "bg-emerald-500" : "animate-pulse-soft bg-indigo-500",
                        )}
                      />
                      {complete ? "Scan complete" : "Live extraction"}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {complete ? "8.2s elapsed" : `${progress}%`}
                    </span>
                  </div>
                  <h2
                    id="live-scan-title"
                    className="text-xl font-semibold tracking-tight text-ink"
                  >
                    {complete ? "Your market moved. We caught it." : "Reading the market in real time."}
                  </h2>
                  <div className="mt-2 flex items-center gap-1.5 text-sm text-slate-500">
                    <Globe2 className="h-3.5 w-3.5 text-slate-400" />
                    <span className="font-mono text-[12px] text-slate-700">{target}</span>
                    <span className="text-slate-300">/</span>
                    <span className="text-[12px]">
                      {scopes.map((scope) => scanScopeLabels[scope]).join(" · ")}
                    </span>
                  </div>
                </div>
                <button
                  ref={closeRef}
                  type="button"
                  onClick={onClose}
                  aria-label="Close panel"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:border-slate-300 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="relative mt-5 h-1.5 overflow-hidden rounded-full bg-slate-100">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-cyan-400"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-7">
              <div className="mb-5 flex items-center justify-between">
                <p className="eyebrow">Execution path</p>
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-400">
                  {complete ? "4 / 4 complete" : `${Math.min(activeIndex + 1, 4)} / 4 in progress`}
                </p>
              </div>

              <div className="space-y-1">
                {STEPS.map((step, index) => {
                  const state = stateFor(index);
                  const Icon = STEP_ICONS[index];
                  return (
                    <div key={step.id} className="relative flex gap-3.5 pb-5 last:pb-0">
                      {index < STEPS.length - 1 ? (
                        <div className="absolute left-[17px] top-8 h-[calc(100%-30px)] w-px bg-slate-200">
                          <div
                            className={cn(
                              "w-px bg-indigo-400 transition-all duration-500",
                              state === "complete" ? "h-full" : "h-0",
                            )}
                          />
                        </div>
                      ) : null}
                      <div
                        className={cn(
                          "relative z-10 mt-0.5 flex h-[35px] w-[35px] shrink-0 items-center justify-center rounded-xl border transition-colors duration-300",
                          state === "complete" &&
                            "border-emerald-200 bg-emerald-50 text-emerald-600",
                          state === "active" &&
                            "border-indigo-200 bg-indigo-50 text-indigo-600 shadow-[0_0_0_4px_rgba(99,102,241,0.06)]",
                          state === "pending" &&
                            "border-slate-200 bg-white text-slate-400",
                        )}
                      >
                        {state === "complete" ? (
                          <Check className="h-4 w-4" strokeWidth={2.5} />
                        ) : state === "active" ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Icon className="h-4 w-4" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1 pt-0.5">
                        <div className="flex items-center justify-between gap-3">
                          <p
                            className={cn(
                              "text-[13px] font-medium",
                              state === "pending" ? "text-slate-400" : "text-slate-900",
                            )}
                          >
                            {step.title}
                          </p>
                          <span className="font-mono text-[10px] text-slate-400">
                            {state === "complete"
                              ? "done"
                              : state === "active"
                                ? "running"
                                : `${((step.endAt - step.startAt) / 1000).toFixed(1)}s`}
                          </span>
                        </div>
                        <p className="mt-0.5 text-[12px] leading-relaxed text-slate-500">
                          {step.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-5 overflow-hidden rounded-xl border border-slate-800 bg-[#0B1120] shadow-inner">
                <div className="flex items-center justify-between border-b border-white/[0.07] px-4 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-400/80" />
                    <span className="h-2 w-2 rounded-full bg-amber-400/80" />
                    <span className="h-2 w-2 rounded-full bg-emerald-400/80" />
                    <span className="ml-2 font-mono text-[10px] tracking-wide text-slate-500">
                      nexus://scan-live
                    </span>
                  </div>
                  <span className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-500">
                    <Circle className="h-1.5 w-1.5 fill-emerald-400 text-emerald-400" />
                    streaming
                  </span>
                </div>
                <div
                  ref={terminalRef}
                  className="h-[188px] overflow-y-auto px-4 py-3 font-mono text-[11px] leading-[1.75]"
                >
                  {visibleLines.map((line) => (
                    <div key={`${line.at}-${line.message}`} className="flex gap-2.5">
                      <span className="shrink-0 text-slate-600">{line.time}</span>
                      <span
                        className={cn(
                          line.level === "success" && "text-emerald-300",
                          line.level === "info" && "text-cyan-200/90",
                          line.level === "muted" && "text-slate-400",
                        )}
                      >
                        {line.message}
                      </span>
                    </div>
                  ))}
                  {!complete ? (
                    <div className="flex gap-2.5">
                      <span className="shrink-0 text-slate-600">···</span>
                      <span className="inline-flex items-center gap-1 text-slate-300">
                        processing
                        <span className="inline-block h-3 w-1.5 animate-blink bg-slate-500" />
                      </span>
                    </div>
                  ) : (
                    <div className="mt-1 flex gap-2.5">
                      <span className="shrink-0 text-slate-600">$</span>
                      <span className="text-slate-300">
                        brief ready
                        <span className="ml-1 inline-block h-3 w-1.5 animate-blink bg-slate-500" />
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="border-t border-slate-200/80 bg-white px-5 py-4 sm:px-7">
              <div className="flex items-center justify-between gap-3">
                <p className="hidden text-[11px] text-slate-400 sm:block">
                  Workspace scan · encrypted at rest
                </p>
                {complete ? (
                  <Link
                    href="/dashboard/competitors/trackline"
                    onClick={onClose}
                    className={cn(buttonVariants({ size: "md" }), "ml-auto")}
                  >
                    Open intelligence brief
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                ) : (
                  <button
                    type="button"
                    onClick={onClose}
                    className={buttonVariants({ variant: "secondary", size: "md" })}
                  >
                    Run in background
                  </button>
                )}
              </div>
            </div>
          </motion.aside>
    </motion.div>
  );
}

const subscribe = () => () => {};

export function LiveExecutionModal({
  open,
  onClose,
  target,
  scopes,
}: LiveExecutionModalProps) {
  const mounted = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {open ? (
        <ScanPanel
          key={`${target}-${scopes.join("-")}`}
          onClose={onClose}
          target={target}
          scopes={scopes}
        />
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
