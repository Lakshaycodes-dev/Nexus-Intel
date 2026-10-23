"use client";

import { FormEvent, useState } from "react";
import {
  ArrowRight,
  Check,
  Globe2,
  Radar,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { ScopeKey } from "@/lib/types";
import { DEFAULT_SCOPES, SCAN_SCOPES } from "@/lib/scopes";
import { cn } from "@/lib/utils";
import { LiveExecutionModal } from "@/components/live-execution-modal";

interface ScannerProps {
  variant?: "hero" | "panel";
  className?: string;
}

function normalizeTarget(input: string) {
  const value = input
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/^www\./i, "")
    .split("/")[0]
    .toLowerCase();

  if (!/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$/.test(value)) {
    return null;
  }
  return value;
}

export function Scanner({ variant = "hero", className }: ScannerProps) {
  const [url, setUrl] = useState("");
  const [scopes, setScopes] = useState<Record<ScopeKey, boolean>>(DEFAULT_SCOPES);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState("");
  const [activeScopes, setActiveScopes] = useState<ScopeKey[]>([
    "pricing",
    "product",
    "news",
  ]);

  const isHero = variant === "hero";

  function toggleScope(scope: ScopeKey) {
    setScopes((current) => ({ ...current, [scope]: !current[scope] }));
    setError("");
  }

  function launch(rawTarget: string) {
    const normalized = normalizeTarget(rawTarget);
    const selected = (Object.keys(scopes) as ScopeKey[]).filter((key) => scopes[key]);

    if (!normalized) {
      setError("Enter a valid public domain, for example acme.com.");
      return;
    }
    if (selected.length === 0) {
      setError("Select at least one scan scope.");
      return;
    }

    setError("");
    setUrl(normalized);
    setTarget(normalized);
    setActiveScopes(selected);
    setOpen(true);
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    launch(url);
  }

  return (
    <>
      <div
        className={cn(
          "relative overflow-hidden rounded-[20px] border bg-white",
          isHero
            ? "border-white/80 p-2 shadow-float"
            : "border-slate-200/80 p-5 shadow-card",
          className,
        )}
      >
        {isHero ? (
          <>
            <div className="flex items-center justify-between gap-3 px-3 pb-2 pt-1.5">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-50 text-indigo-600">
                  <Radar className="h-3.5 w-3.5" />
                </span>
                <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Quick market scan
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setUrl("trackline.io");
                  launch("trackline.io");
                }}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-indigo-600 transition hover:text-indigo-800"
              >
                <Sparkles className="h-3 w-3" />
                Try a sample
              </button>
            </div>

            <form onSubmit={onSubmit}>
              <div className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-slate-50/70 p-2 sm:flex-row sm:items-center">
                <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-xl bg-white px-3.5 shadow-sm ring-1 ring-slate-200/70 transition focus-within:ring-2 focus-within:ring-indigo-400/30">
                  <Globe2 className="h-4 w-4 shrink-0 text-slate-400" />
                  <input
                    value={url}
                    onChange={(event) => {
                      setUrl(event.target.value);
                      setError("");
                    }}
                    aria-label="Competitor URL"
                    placeholder="Enter competitor URL, e.g., acme.com"
                    spellCheck={false}
                    autoComplete="off"
                    className="h-11 min-w-0 flex-1 border-0 bg-transparent p-0 text-sm text-slate-900 placeholder:text-slate-400 focus:ring-0"
                  />
                  <span className="hidden rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-400 sm:inline">
                    URL
                  </span>
                </div>
                <button
                  type="submit"
                  className="group inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-indigo-500 to-indigo-600 px-5 text-[13px] font-semibold text-white shadow-[0_1px_2px_rgba(15,23,42,0.2),0_8px_20px_-8px_rgba(79,70,229,0.7)] transition hover:to-indigo-700 active:translate-y-px"
                >
                  RUN SCAN
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </button>
              </div>

              <div className="flex flex-col gap-2.5 px-2.5 pb-2 pt-3.5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mr-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                    Scope
                  </span>
                  {SCAN_SCOPES.map((scope) => {
                    const checked = scopes[scope.key];
                    return (
                      <button
                        key={scope.key}
                        type="button"
                        role="checkbox"
                        aria-checked={checked}
                        onClick={() => toggleScope(scope.key)}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition",
                          checked
                            ? "border-indigo-200 bg-indigo-50/80 text-indigo-700"
                            : "border-slate-200 bg-white text-slate-500 hover:border-slate-300",
                        )}
                      >
                        <span
                          className={cn(
                            "flex h-3.5 w-3.5 items-center justify-center rounded-[4px] border transition",
                            checked
                              ? "border-indigo-500 bg-indigo-500 text-white"
                              : "border-slate-300 bg-white",
                          )}
                        >
                          {checked ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : null}
                        </span>
                        {scope.label}
                      </button>
                    );
                  })}
                </div>
                <span className="flex items-center gap-1.5 text-[10px] text-slate-400">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                  Read-only · no login required
                </span>
              </div>
            </form>
          </>
        ) : (
          <form onSubmit={onSubmit}>
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-sm">
                    <Radar className="h-3.5 w-3.5" />
                  </span>
                  <h2 className="text-[15px] font-semibold text-ink">
                    Initiate a new intelligence scan
                  </h2>
                </div>
                <p className="text-[13px] text-slate-500">
                  Point Nexus at any public competitor surface. We will map the rest.
                </p>
              </div>
              <span className="hidden items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-medium text-slate-500 md:flex">
                <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-emerald-500" />
                Engine ready
              </span>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-xl border border-slate-200 bg-white px-3.5 shadow-sm transition focus-within:border-indigo-300 focus-within:ring-4 focus-within:ring-indigo-500/10">
                <Globe2 className="h-4 w-4 shrink-0 text-slate-400" />
                <input
                  value={url}
                  onChange={(event) => {
                    setUrl(event.target.value);
                    setError("");
                  }}
                  aria-label="Competitor URL"
                  placeholder="competitor.com"
                  spellCheck={false}
                  autoComplete="off"
                  className="h-11 min-w-0 flex-1 border-0 bg-transparent p-0 text-sm text-slate-900 placeholder:text-slate-400 focus:ring-0"
                />
              </div>
              <button
                type="submit"
                className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 text-[13px] font-semibold text-white shadow-sm transition hover:bg-slate-800 active:translate-y-px"
              >
                Run scan
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {SCAN_SCOPES.map((scope) => {
                const checked = scopes[scope.key];
                return (
                  <button
                    key={scope.key}
                    type="button"
                    role="checkbox"
                    aria-checked={checked}
                    onClick={() => toggleScope(scope.key)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition",
                      checked
                        ? "border-indigo-200 bg-indigo-50/80 text-indigo-700"
                        : "border-slate-200 bg-white text-slate-500 hover:border-slate-300",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-3.5 w-3.5 items-center justify-center rounded-[4px] border",
                        checked
                          ? "border-indigo-500 bg-indigo-500 text-white"
                          : "border-slate-300 bg-white",
                      )}
                    >
                      {checked ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : null}
                    </span>
                    {scope.label}
                  </button>
                );
              })}
            </div>
          </form>
        )}

        {error ? (
          <p role="alert" className="px-2 pb-1 pt-2 text-[11px] font-medium text-rose-600">
            {error}
          </p>
        ) : null}
      </div>

      <LiveExecutionModal
        open={open}
        onClose={() => setOpen(false)}
        target={target}
        scopes={activeScopes}
      />
    </>
  );
}
