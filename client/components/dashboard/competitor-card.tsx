import Link from "next/link";
import {
  ArrowDownUp,
  ArrowUpRight,
  Clock3,
  MoreHorizontal,
  Sparkles,
} from "lucide-react";
import type { Competitor } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const threatVariant = {
  "High Movement": "high",
  Watching: "watching",
  Stable: "stable",
} as const;

export function CompetitorCard({ competitor }: { competitor: Competitor }) {
  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card transition-all duration-300 hover:-translate-y-0.5 hover:border-slate-300/80 hover:shadow-card-hover">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-[11px] font-semibold text-white shadow-sm",
              competitor.accent.gradient,
            )}
          >
            {competitor.monogram}
          </span>
          <div className="min-w-0">
            <h3 className="truncate text-[14px] font-semibold tracking-tight text-ink">
              {competitor.name}
            </h3>
            <p className="mt-0.5 truncate font-mono text-[10px] text-slate-400">
              {competitor.domain}
            </p>
          </div>
        </div>
        <button
          type="button"
          aria-label={`More options for ${competitor.name}`}
          className="-mr-1 -mt-1 flex h-7 w-7 items-center justify-center rounded-md text-slate-300 transition hover:bg-slate-50 hover:text-slate-500"
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <Badge variant={threatVariant[competitor.threatLevel]}>
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              competitor.threatLevel === "High Movement" && "animate-pulse-soft bg-amber-500",
              competitor.threatLevel === "Watching" && "bg-violet-500",
              competitor.threatLevel === "Stable" && "bg-emerald-500",
            )}
          />
          {competitor.threatLevel}
        </Badge>
        <span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[9px] font-medium text-slate-500">
          {competitor.tierRange}
        </span>
      </div>

      <p className="mt-4 line-clamp-2 min-h-[36px] text-[11.5px] leading-relaxed text-slate-500">
        {competitor.latestChange}
      </p>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <div className="flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50/60 px-2.5 py-2">
          <ArrowDownUp className="h-3 w-3 text-amber-500" />
          <div>
            <p className="text-[10px] font-semibold text-slate-700">{competitor.priceChanges}</p>
            <p className="text-[8px] text-slate-400">price changes</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50/60 px-2.5 py-2">
          <Sparkles className="h-3 w-3 text-indigo-500" />
          <div>
            <p className="text-[10px] font-semibold text-slate-700">
              {competitor.featureLaunches}
            </p>
            <p className="text-[8px] text-slate-400">new launches</p>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3.5">
        <span className="flex items-center gap-1.5 text-[9px] text-slate-400">
          <Clock3 className="h-3 w-3" />
          Scanned {competitor.lastScan}
        </span>
        <Link
          href={`/dashboard/competitors/${competitor.id}`}
          className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-500 transition-colors group-hover:text-indigo-600"
        >
          View deep dive
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>
    </article>
  );
}
