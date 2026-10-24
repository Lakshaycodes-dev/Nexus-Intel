"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowDownUp,
  ArrowUpRight,
  Megaphone,
  Newspaper,
  Rocket,
  Sparkles,
} from "lucide-react";
import { marketSignals } from "@/lib/data";
import { cn } from "@/lib/utils";

type Filter = "All" | "Pricing" | "Product" | "News";

const filters: Filter[] = ["All", "Pricing", "Product", "News"];

function signalIcon(type: string) {
  if (type === "Pricing Update") return ArrowDownUp;
  if (type === "Product Update") return Sparkles;
  if (type === "Press Release") return Megaphone;
  if (type === "Product Hunt") return Rocket;
  return Newspaper;
}

function matchesFilter(type: string, filter: Filter) {
  if (filter === "All") return true;
  if (filter === "Pricing") return type === "Pricing Update";
  if (filter === "Product") return type === "Product Update";
  return type === "News" || type === "Press Release" || type === "Product Hunt";
}

export function SignalFeed() {
  const [filter, setFilter] = useState<Filter>("All");
  const signals = marketSignals.filter((signal) => matchesFilter(signal.type, filter));

  return (
    <section
      id="signals"
      className="scroll-mt-24 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card lg:sticky lg:top-[84px]"
    >
      <div className="border-b border-slate-100 px-5 pb-3 pt-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[14px] font-semibold tracking-tight text-ink">
                Live market signals
              </h2>
              <span className="flex items-center gap-1 rounded-full border border-emerald-100 bg-emerald-50 px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.1em] text-emerald-700">
                <span className="h-1 w-1 animate-pulse-soft rounded-full bg-emerald-500" />
                Live
              </span>
            </div>
            <p className="mt-1 text-[10px] text-slate-400">Off-site moves across your watchlist</p>
          </div>
          <button
            type="button"
            aria-label="Open signal feed"
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 text-slate-400 transition hover:text-slate-700"
          >
            <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="mt-3.5 flex items-center gap-1">
          {filters.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              className={cn(
                "rounded-full px-2.5 py-1 text-[9px] font-medium transition",
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

      <div className="divide-y divide-slate-100">
        {signals.map((signal) => {
          const Icon = signalIcon(signal.type);
          return (
            <Link
              key={signal.id}
              href={`/dashboard/competitors/${signal.competitorId}`}
              className="group flex gap-3 px-5 py-4 transition-colors hover:bg-slate-50/70"
            >
              <span
                className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border"
                style={{
                  color: signal.accent.hex,
                  backgroundColor: `${signal.accent.hex}10`,
                  borderColor: `${signal.accent.hex}22`,
                }}
              >
                <Icon className="h-3 w-3" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[9px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                    {signal.type}
                  </span>
                  <span
                    className={cn(
                      "shrink-0 rounded px-1.5 py-0.5 text-[8px] font-semibold",
                      signal.impact === "High" && "bg-amber-50 text-amber-700",
                      signal.impact === "Medium" && "bg-indigo-50 text-indigo-600",
                      signal.impact === "Low" && "bg-slate-100 text-slate-500",
                    )}
                  >
                    {signal.impact}
                  </span>
                </div>
                <p className="mt-1 text-[11.5px] font-medium leading-snug text-slate-700 transition-colors group-hover:text-indigo-700">
                  {signal.title}
                </p>
                <div className="mt-1.5 flex items-center gap-1.5 text-[9px] text-slate-400">
                  <span className="font-medium text-slate-500">{signal.competitor}</span>
                  <span className="h-0.5 w-0.5 rounded-full bg-slate-300" />
                  <span className="truncate">{signal.source}</span>
                  <span className="h-0.5 w-0.5 rounded-full bg-slate-300" />
                  <span className="shrink-0">{signal.time}</span>
                </div>
              </div>
            </Link>
          );
        })}
        {signals.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-[12px] font-medium text-slate-600">No signals in this view.</p>
            <p className="mt-1 text-[10px] text-slate-400">Try a broader filter.</p>
          </div>
        ) : null}
      </div>

      <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/50 px-5 py-3">
        <span className="text-[9px] text-slate-400">Updated 8 min ago</span>
        <Link
          href="/dashboard#signals"
          className="inline-flex items-center gap-1 text-[9px] font-semibold text-slate-500 hover:text-indigo-600"
        >
          View all signals
          <ArrowUpRight className="h-2.5 w-2.5" />
        </Link>
      </div>
    </section>
  );
}
