"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Bell,
  ChevronRight,
  Download,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import type { Competitor, ScopeKey } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LiveExecutionModal } from "@/components/live-execution-modal";
import { cn } from "@/lib/utils";

const threatVariant = {
  "High Movement": "high",
  Watching: "watching",
  Stable: "stable",
} as const;

export function CompetitorHeader({ competitor }: { competitor: Competitor }) {
  const [scanOpen, setScanOpen] = useState(false);
  const [following, setFollowing] = useState(true);
  const scopes: ScopeKey[] = ["pricing", "product", "news"];

  return (
    <>
      <div
        className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card"
        style={{
          backgroundImage: `linear-gradient(115deg, ${competitor.accent.hex}0C, transparent 42%)`,
        }}
      >
        <div className="pointer-events-none absolute -right-12 -top-20 h-56 w-56 rounded-full bg-gradient-to-br from-indigo-100/50 to-cyan-100/40 blur-3xl" />

        <div className="relative border-b border-slate-100 px-5 py-3.5 sm:px-6">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
            <Link
              href="/dashboard"
              className="flex items-center gap-1 transition-colors hover:text-slate-700"
            >
              <ArrowLeft className="h-3 w-3" />
              Overview
            </Link>
            <ChevronRight className="h-2.5 w-2.5 text-slate-300" />
            <Link href="/dashboard#competitors" className="transition-colors hover:text-slate-700">
              Competitors
            </Link>
            <ChevronRight className="h-2.5 w-2.5 text-slate-300" />
            <span className="font-medium text-slate-600">{competitor.name}</span>
          </div>
        </div>

        <div className="relative flex flex-col gap-5 px-5 py-6 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <span
              className={cn(
                "flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br text-[16px] font-semibold text-white shadow-[0_8px_24px_-8px_rgba(15,23,42,0.4)]",
                competitor.accent.gradient,
              )}
            >
              {competitor.monogram}
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-[26px] font-semibold tracking-[-0.035em] text-ink">
                  {competitor.name}
                </h1>
                <Badge variant={threatVariant[competitor.threatLevel]}>
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      competitor.threatLevel === "High Movement" &&
                        "animate-pulse-soft bg-amber-500",
                      competitor.threatLevel === "Watching" && "bg-violet-500",
                      competitor.threatLevel === "Stable" && "bg-emerald-500",
                    )}
                  />
                  {competitor.threatLevel}
                </Badge>
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-2.5 text-[11px] text-slate-400">
                <a
                  href={`https://${competitor.domain}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-500 transition hover:text-indigo-600"
                >
                  {competitor.domain}
                  <ExternalLink className="h-2.5 w-2.5" />
                </a>
                <span className="h-3 w-px bg-slate-200" />
                <span>{competitor.category}</span>
                <span className="h-3 w-px bg-slate-200" />
                <span className="inline-flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  Monitored · scanned {competitor.lastScan}
                </span>
              </div>
              <p className="mt-2 max-w-xl text-[12px] leading-relaxed text-slate-500">
                {competitor.tagline}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setFollowing((value) => !value)}
              className={cn(
                "inline-flex h-9 items-center gap-1.5 rounded-full border px-3 text-[11px] font-medium transition",
                following
                  ? "border-indigo-100 bg-indigo-50 text-indigo-700"
                  : "border-slate-200 bg-white text-slate-500 hover:border-slate-300",
              )}
            >
              <Bell className={cn("h-3.5 w-3.5", following && "fill-indigo-100")} />
              {following ? "Following" : "Follow"}
            </button>
            <Button
              variant="secondary"
              size="sm"
              className="h-9"
              onClick={() => window.print()}
            >
              <Download className="h-3.5 w-3.5" />
              Export matrix PDF
            </Button>
            <Button size="sm" className="h-9" onClick={() => setScanOpen(true)}>
              <RefreshCw className="h-3.5 w-3.5" />
              Force re-scan
            </Button>
          </div>
        </div>
      </div>

      <LiveExecutionModal
        open={scanOpen}
        onClose={() => setScanOpen(false)}
        target={competitor.domain}
        scopes={scopes}
      />
    </>
  );
}
