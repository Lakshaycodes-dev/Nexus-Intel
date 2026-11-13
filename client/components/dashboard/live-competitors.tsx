"use client";

import { Radio } from "lucide-react";

import { CompetitorCard } from "@/components/dashboard/competitor-card";
import { useLiveCompetitors } from "@/lib/use-live-competitors";
import type { Competitor } from "@/lib/types";
import { cn } from "@/lib/utils";

export function LiveCompetitors({
  initialCompetitors,
}: {
  initialCompetitors: Competitor[];
}) {
  const { competitors, loading, liveCount } = useLiveCompetitors(initialCompetitors);

  return (
    <>
      <div className="mt-2 flex items-center gap-1.5 text-[9px] text-slate-400">
        <Radio
          className={cn(
            "h-2.5 w-2.5",
            loading ? "animate-pulse-soft text-indigo-400" : "text-emerald-500",
          )}
        />
        {loading
          ? "Syncing the watchlist with the Nexus-Intel API…"
          : liveCount > 0
            ? `Live API · ${liveCount} of ${competitors.length} domains have stored analysis runs`
            : "Showing the cached watchlist · run a scan to populate live analyses"}
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {competitors.map((competitor) => (
          <CompetitorCard key={competitor.id} competitor={competitor} />
        ))}
      </div>
    </>
  );
}
