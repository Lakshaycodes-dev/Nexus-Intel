"use client";

import { useState } from "react";
import {
  ArrowDownUp,
  ArrowUpRight,
  Megaphone,
  Newspaper,
  Rocket,
  Sparkles,
} from "lucide-react";
import type { Mention, MentionType } from "@/lib/types";
import { cn } from "@/lib/utils";

type Filter = "All" | "News" | "Press" | "Product Hunt";

const filters: Filter[] = ["All", "News", "Press", "Product Hunt"];

const typeStyles: Record<MentionType, string> = {
  News: "border-sky-100 bg-sky-50 text-sky-700",
  "Press Release": "border-violet-100 bg-violet-50 text-violet-700",
  "Product Hunt": "border-amber-100 bg-amber-50 text-amber-700",
  "Pricing Update": "border-indigo-100 bg-indigo-50 text-indigo-700",
  "Product Update": "border-emerald-100 bg-emerald-50 text-emerald-700",
};

function iconFor(type: MentionType) {
  if (type === "News") return Newspaper;
  if (type === "Press Release") return Megaphone;
  if (type === "Product Hunt") return Rocket;
  if (type === "Pricing Update") return ArrowDownUp;
  return Sparkles;
}

function matchesFilter(type: MentionType, filter: Filter) {
  if (filter === "All") return true;
  if (filter === "News") return type === "News";
  if (filter === "Press") return type === "Press Release";
  return type === "Product Hunt";
}

export function MentionsFeed({ mentions }: { mentions: Mention[] }) {
  const [filter, setFilter] = useState<Filter>("All");
  const filtered = mentions.filter((mention) => matchesFilter(mention.type, filter));

  return (
    <section
      id="mentions"
      className="print-avoid-break scroll-mt-24 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card"
    >
      <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-ink">
            Off-site mentions
          </h2>
          <p className="mt-1 text-[11px] text-slate-500">
            News, press, and community signals from the last 30 days.
          </p>
        </div>
        <div className="flex items-center gap-1 overflow-x-auto">
          {filters.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              className={cn(
                "shrink-0 rounded-full px-2.5 py-1.5 text-[9px] font-medium transition",
                filter === item
                  ? "bg-slate-900 text-white"
                  : "text-slate-400 hover:bg-slate-100 hover:text-slate-600",
              )}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="px-5 py-2 sm:px-6">
        {filtered.length > 0 ? (
          <div className="relative">
            <div className="absolute bottom-6 left-[13px] top-6 w-px bg-slate-100" />
            {filtered.map((mention) => {
              const Icon = iconFor(mention.type);
              return (
                <article
                  key={mention.id}
                  className="group relative flex gap-4 border-b border-slate-100 py-4 last:border-b-0"
                >
                  <span className="relative z-10 mt-0.5 flex h-[27px] w-[27px] shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-400 shadow-[0_0_0_4px_white]">
                    <Icon className="h-3 w-3" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={cn(
                          "rounded border px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.08em]",
                          typeStyles[mention.type],
                        )}
                      >
                        {mention.type}
                      </span>
                      <span className="text-[9px] text-slate-400">{mention.source}</span>
                      <span className="h-0.5 w-0.5 rounded-full bg-slate-300" />
                      <span className="text-[9px] text-slate-400">{mention.time}</span>
                      {mention.sentiment === "positive" ? (
                        <span className="ml-auto hidden items-center gap-1 text-[8px] font-medium text-emerald-600 sm:flex">
                          <span className="h-1 w-1 rounded-full bg-emerald-500" />
                          Positive
                        </span>
                      ) : mention.sentiment === "negative" ? (
                        <span className="ml-auto hidden items-center gap-1 text-[8px] font-medium text-rose-500 sm:flex">
                          <span className="h-1 w-1 rounded-full bg-rose-500" />
                          Negative
                        </span>
                      ) : null}
                    </div>
                    <h3 className="mt-1.5 text-[12px] font-semibold leading-snug text-slate-800">
                      {mention.title}
                    </h3>
                    <p className="mt-1 max-w-2xl text-[10.5px] leading-relaxed text-slate-500">
                      {mention.summary}
                    </p>
                  </div>
                  <ArrowUpRight className="mt-1 hidden h-3.5 w-3.5 shrink-0 text-slate-300 transition-colors group-hover:text-indigo-500 sm:block" />
                </article>
              );
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-50 text-slate-300">
              <Newspaper className="h-4 w-4" />
            </span>
            <p className="mt-2 text-[11px] font-medium text-slate-600">
              No {filter.toLowerCase()} mentions this cycle.
            </p>
            <p className="mt-0.5 text-[9px] text-slate-400">
              Try another signal type or check back after the next scan.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
