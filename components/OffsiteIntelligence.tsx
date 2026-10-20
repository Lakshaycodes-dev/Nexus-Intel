"use client";

import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  Minus,
  Newspaper,
  Radio,
  SearchX,
  TrendingUp,
  TriangleAlert,
} from "lucide-react";
import type { CompetitorData, Sentiment } from "@/lib/mockData";

type Filter = "all" | Sentiment;

const SENTIMENT_CONFIG = {
  positive: {
    label: "Positive",
    chip: "border-emerald-400/25 bg-emerald-400/[0.08] text-emerald-300",
    icon: TrendingUp,
    dot: "bg-emerald-400",
  },
  neutral: {
    label: "Neutral",
    chip: "border-slate-400/20 bg-slate-400/[0.07] text-slate-300",
    icon: Minus,
    dot: "bg-slate-400",
  },
  threat: {
    label: "Threat",
    chip: "border-rose-400/25 bg-rose-500/[0.08] text-rose-300",
    icon: TriangleAlert,
    dot: "bg-rose-400",
  },
} as const;

const SOURCE_STYLES: { match: string; className: string }[] = [
  { match: "techcrunch", className: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300" },
  { match: "reddit", className: "border-orange-400/20 bg-orange-400/10 text-orange-300" },
  { match: "reuters", className: "border-sky-400/20 bg-sky-400/10 text-sky-300" },
  { match: "gartner", className: "border-indigo-400/20 bg-indigo-400/10 text-indigo-300" },
  { match: "hacker", className: "border-amber-400/20 bg-amber-400/10 text-amber-300" },
  { match: "business", className: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300" },
];

function sourceStyle(source: string) {
  return (
    SOURCE_STYLES.find((style) => source.toLowerCase().includes(style.match))
      ?.className ?? "border-white/10 bg-white/[0.04] text-slate-300"
  );
}

function displayHost(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

interface OffsiteIntelligenceProps {
  data: CompetitorData;
}

export default function OffsiteIntelligence({ data }: OffsiteIntelligenceProps) {
  const [filter, setFilter] = useState<Filter>("all");

  const counts = useMemo(() => {
    return data.offsiteNews.reduce(
      (accumulator, item) => {
        accumulator[item.sentiment] += 1;
        return accumulator;
      },
      { positive: 0, neutral: 0, threat: 0 },
    );
  }, [data.offsiteNews]);

  const filtered = useMemo(
    () =>
      filter === "all"
        ? data.offsiteNews
        : data.offsiteNews.filter((item) => item.sentiment === filter),
    [data.offsiteNews, filter],
  );

  const filters: { key: Filter; label: string; count: number }[] = [
    { key: "all", label: "All", count: data.offsiteNews.length },
    { key: "positive", label: "Positive", count: counts.positive },
    { key: "neutral", label: "Neutral", count: counts.neutral },
    { key: "threat", label: "Threat", count: counts.threat },
  ];

  return (
    <section className="glass-panel relative flex flex-col overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-400/40 to-transparent" />

      <div className="flex items-start justify-between gap-3 border-b border-white/[0.06] p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-sky-400/20 bg-sky-500/[0.08]">
            <Newspaper className="h-4 w-4 text-sky-300" />
          </span>
          <div>
            <h2 className="text-[15px] font-semibold tracking-tight text-white">
              Off-site intelligence
            </h2>
            <p className="text-[11px] text-slate-500">
              Press, releases &amp; forum chatter
            </p>
          </div>
        </div>
        <span className="chip shrink-0 border-sky-400/15 bg-sky-500/[0.05] text-sky-200/70">
          <Radio className="h-3 w-3" />
          Search API
        </span>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-white/[0.05] px-4 py-2.5">
        {filters.map((item) => {
          const active = filter === item.key;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => setFilter(item.key)}
              aria-pressed={active}
              className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-[10.5px] font-medium transition-colors focus-ring ${
                active
                  ? "bg-white/[0.08] text-white"
                  : "text-slate-500 hover:bg-white/[0.03] hover:text-slate-300"
              }`}
            >
              {item.key !== "all" && (
                <span
                  className={`h-1.5 w-1.5 rounded-full ${SENTIMENT_CONFIG[item.key].dot}`}
                />
              )}
              {item.label}
              <span
                className={`font-mono text-[9px] ${
                  active ? "text-slate-400" : "text-slate-600"
                }`}
              >
                {item.count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex-1 space-y-2 p-4">
        {filtered.length === 0 ? (
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center rounded-xl border border-dashed border-white/10 text-center">
            <SearchX className="h-5 w-5 text-slate-600" />
            <p className="mt-2 text-[11px] text-slate-500">
              No {filter} signals in this snapshot.
            </p>
          </div>
        ) : (
          filtered.map((item) => {
            const sentiment = SENTIMENT_CONFIG[item.sentiment];
            const SentimentIcon = sentiment.icon;

            return (
              <a
                key={`${item.source}-${item.title}`}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group block rounded-xl border border-white/[0.06] bg-white/[0.018] p-3.5 transition-all duration-200 hover:border-white/[0.14] hover:bg-white/[0.04]"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md border font-mono text-[10px] font-semibold uppercase ${sourceStyle(
                        item.source,
                      )}`}
                    >
                      {item.source.charAt(0)}
                    </span>
                    <span className="truncate text-[10px] font-medium text-slate-400">
                      {item.source}
                    </span>
                  </div>
                  <span
                    className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-1.5 py-0.5 text-[9px] font-medium ${sentiment.chip}`}
                  >
                    <SentimentIcon className="h-2.5 w-2.5" />
                    {sentiment.label}
                  </span>
                </div>

                <h3 className="mt-2 text-[12px] font-medium leading-snug text-slate-200 transition-colors group-hover:text-white">
                  {item.title}
                </h3>

                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="truncate font-mono text-[9px] text-slate-600">
                    {displayHost(item.url)}
                  </span>
                  <span className="flex shrink-0 items-center gap-0.5 text-[9px] font-medium text-slate-500 transition-colors group-hover:text-indigo-300">
                    Read
                    <ArrowUpRight className="h-3 w-3 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                  </span>
                </div>
              </a>
            );
          })
        )}
      </div>

      <div className="border-t border-white/[0.05] px-4 py-2.5 text-[9.5px] text-slate-600">
        Sentiment classified by Gemini 1.5 Flash · {data.offsiteNews.length}{" "}
        sources indexed
      </div>
    </section>
  );
}
