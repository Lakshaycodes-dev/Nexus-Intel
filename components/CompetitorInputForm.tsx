"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowRight,
  Check,
  Globe2,
  ListTree,
  Loader2,
  Newspaper,
  Play,
  ShieldCheck,
  Sparkles,
  Tags,
} from "lucide-react";
import type { AnalysisOptions } from "@/lib/api";
import { DEFAULT_ANALYSIS_OPTIONS } from "@/lib/api";
import { normalizeDomain } from "@/lib/mockData";

interface CompetitorInputFormProps {
  onSubmit: (domain: string, options: AnalysisOptions) => void;
  isLoading: boolean;
  defaultDomain?: string;
}

const PARAMETERS: {
  key: keyof AnalysisOptions;
  title: string;
  hint: string;
  icon: typeof Tags;
}[] = [
  {
    key: "pricingTiers",
    title: "Pricing Tiers",
    hint: "Plans, prices & packaging",
    icon: Tags,
  },
  {
    key: "featureAccordions",
    title: "Feature Accordions",
    hint: "Expand hidden dynamic toggles",
    icon: ListTree,
  },
  {
    key: "offsiteMentions",
    title: "Off-site Mentions",
    hint: "Press, Reddit & analyst chatter",
    icon: Newspaper,
  },
];

const SUGGESTIONS = ["stripe.com", "acme.com", "linear.app", "notion.so"];

export default function CompetitorInputForm({
  onSubmit,
  isLoading,
  defaultDomain = "stripe.com",
}: CompetitorInputFormProps) {
  const [domain, setDomain] = useState(defaultDomain);
  const [options, setOptions] = useState<AnalysisOptions>(DEFAULT_ANALYSIS_OPTIONS);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDomain(defaultDomain);
  }, [defaultDomain]);

  const enabledCount = Object.values(options).filter(Boolean).length;

  function toggleOption(key: keyof AnalysisOptions) {
    setOptions((previous) => ({ ...previous, [key]: !previous[key] }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalized = normalizeDomain(domain);
    if (!normalized || !/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(normalized)) {
      setError("Enter a valid domain, for example stripe.com");
      return;
    }

    if (enabledCount === 0) {
      setError("Select at least one analysis parameter.");
      return;
    }

    setError(null);
    onSubmit(normalized, options);
  }

  return (
    <div className="glass-panel-strong relative overflow-hidden p-5 sm:p-6">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-400/70 to-transparent" />
      <div className="pointer-events-none absolute -right-20 -top-24 h-52 w-52 rounded-full bg-indigo-500/15 blur-3xl" />

      <div className="relative">
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-md border border-indigo-400/25 bg-indigo-500/15">
                <Sparkles className="h-3.5 w-3.5 text-indigo-300" />
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-indigo-300/80">
                New intelligence run
              </span>
            </div>
            <h2 className="text-lg font-semibold tracking-tight text-white">
              Target a competitor
            </h2>
            <p className="mt-1 text-[12.5px] leading-relaxed text-slate-400">
              Discovery, interaction, extraction and storage — handled end to end.
            </p>
          </div>
          <span className="chip shrink-0 border-indigo-400/20 bg-indigo-500/[0.08] text-indigo-200/80">
            Autonomous
          </span>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label
              htmlFor="competitor-domain"
              className="mb-1.5 block text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500"
            >
              Competitor domain
            </label>
            <div
              className={`group flex items-center gap-2 rounded-xl border bg-ink-950/70 px-3 transition-all duration-200 focus-within:border-indigo-400/60 focus-within:shadow-glow-sm ${
                error ? "border-rose-400/50" : "border-white/10 hover:border-white/20"
              }`}
            >
              <Globe2 className="h-4 w-4 shrink-0 text-slate-500 transition-colors group-focus-within:text-indigo-300" />
              <span className="select-none font-mono text-[12px] text-slate-600">
                https://
              </span>
              <input
                id="competitor-domain"
                name="domain"
                type="text"
                inputMode="url"
                autoComplete="off"
                spellCheck={false}
                value={domain}
                onChange={(event) => {
                  setDomain(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="stripe.com"
                aria-invalid={Boolean(error)}
                aria-describedby={error ? "domain-error" : undefined}
                disabled={isLoading}
                className="h-11 w-full bg-transparent font-mono text-sm text-white placeholder:text-slate-600 focus:outline-none disabled:opacity-60"
              />
            </div>
            {error ? (
              <p id="domain-error" className="mt-1.5 text-[11px] text-rose-300">
                {error}
              </p>
            ) : (
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <span className="text-[10px] uppercase tracking-wider text-slate-600">
                  Try
                </span>
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    disabled={isLoading}
                    onClick={() => {
                      setDomain(suggestion);
                      setError(null);
                    }}
                    className="rounded-md border border-white/[0.07] bg-white/[0.025] px-1.5 py-0.5 font-mono text-[10px] text-slate-500 transition hover:border-indigo-400/30 hover:bg-indigo-500/10 hover:text-indigo-300 disabled:opacity-50"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
                Analysis parameters
              </span>
              <span className="font-mono text-[10px] text-slate-600">
                {enabledCount}/3 enabled
              </span>
            </div>
            <div className="space-y-1.5">
              {PARAMETERS.map((parameter) => {
                const Icon = parameter.icon;
                const checked = options[parameter.key];

                return (
                  <label
                    key={parameter.key}
                    className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 transition-all duration-200 ${
                      checked
                        ? "border-indigo-400/25 bg-indigo-500/[0.07]"
                        : "border-white/[0.06] bg-white/[0.015] hover:border-white/15 hover:bg-white/[0.03]"
                    } ${isLoading ? "pointer-events-none opacity-70" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleOption(parameter.key)}
                      disabled={isLoading}
                      className="sr-only"
                    />
                    <span
                      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-[5px] border transition-all ${
                        checked
                          ? "border-indigo-400 bg-indigo-500 text-white"
                          : "border-slate-600 bg-transparent text-transparent"
                      }`}
                    >
                      <Check className="h-3 w-3" strokeWidth={3} />
                    </span>
                    <span className="flex min-w-0 flex-1 items-center gap-2">
                      <Icon
                        className={`h-3.5 w-3.5 shrink-0 ${
                          checked ? "text-indigo-300" : "text-slate-500"
                        }`}
                      />
                      <span className="min-w-0">
                        <span
                          className={`block truncate text-[12.5px] font-medium ${
                            checked ? "text-slate-200" : "text-slate-400"
                          }`}
                        >
                          {parameter.title}
                        </span>
                        <span className="block truncate text-[10.5px] text-slate-500">
                          {parameter.hint}
                        </span>
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-indigo-500 via-indigo-500 to-sky-500 px-4 py-3 text-[13px] font-semibold text-white shadow-glow transition-all duration-300 hover:brightness-110 focus-ring disabled:cursor-not-allowed disabled:opacity-85 disabled:shadow-none"
          >
            <span className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4 fill-white/20" />
            )}
            <span className="relative">
              {isLoading ? "Deploying autonomous agents…" : "Start Autonomous Intelligence Run"}
            </span>
            {!isLoading && (
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            )}
          </button>

          <div className="flex items-center justify-center gap-1.5 text-[10px] text-slate-600">
            <ShieldCheck className="h-3 w-3" />
            Read-only crawl · No credentials required · Snapshot persisted to MongoDB
          </div>
        </form>
      </div>
    </div>
  );
}
