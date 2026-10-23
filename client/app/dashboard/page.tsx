import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowLeftRight,
  ArrowUpRight,
  Compass,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { competitors } from "@/lib/data";
import { MetricCard } from "@/components/dashboard/metric-card";
import { CompetitorCard } from "@/components/dashboard/competitor-card";
import { SignalFeed } from "@/components/dashboard/signal-feed";
import { Scanner } from "@/components/scanner";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Market Overview",
  description: "Monitor price movements, feature launches, and market signals across your watchlist.",
};

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-100 bg-emerald-50 px-2 py-1 text-[8px] font-semibold uppercase tracking-[0.12em] text-emerald-700">
              <span className="h-1 w-1 animate-pulse-soft rounded-full bg-emerald-500" />
              Live overview
            </span>
            <span className="text-[10px] text-slate-400">Wednesday, October 21</span>
            <span className="hidden h-3 w-px bg-slate-200 sm:inline" />
            <span className="hidden items-center gap-1 text-[10px] text-slate-400 sm:flex">
              <RefreshCw className="h-2.5 w-2.5" />
              Synced 8 min ago
            </span>
          </div>
          <h1 className="mt-3 text-[28px] font-semibold tracking-[-0.035em] text-ink sm:text-[32px]">
            Good morning, Alex.
          </h1>
          <p className="mt-1.5 max-w-xl text-[12.5px] leading-relaxed text-slate-500">
            Your market moved 14 times since your last visit. Three changes deserve your
            attention before your next call.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/dashboard/compare"
            className={cn(buttonVariants({ variant: "secondary", size: "md" }), "h-9 px-3.5")}
          >
            <ArrowLeftRight className="h-3.5 w-3.5" />
            Compare market
          </Link>
          <Link href="#scan" className={cn(buttonVariants({ size: "md" }), "h-9 px-4")}>
            <ScanSearch className="h-3.5 w-3.5" />
            New scan
          </Link>
        </div>
      </header>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total competitors tracked"
          value="8"
          trend="+2"
          trendDirection="up"
          detail="Across 6 market categories"
          icon={Compass}
          tone="indigo"
          values={[3, 4, 4, 5, 6, 6, 7, 8, 8]}
          sparklineId="competitors"
        />
        <MetricCard
          label="Price changes detected"
          value="3"
          trend="+3 this week"
          trendDirection="up"
          detail="Trackline changed twice"
          icon={TrendingUp}
          tone="amber"
          values={[1, 1, 2, 1, 2, 3, 2, 3, 3]}
          sparklineId="pricing"
        />
        <MetricCard
          label="New feature launches"
          value="5"
          trend="4 in 48h"
          trendDirection="up"
          detail="Compass HQ leads this week"
          icon={Sparkles}
          tone="cyan"
          values={[2, 1, 2, 2, 3, 2, 4, 4, 5]}
          sparklineId="features"
        />
        <MetricCard
          label="System health"
          value="100%"
          trend="Operational"
          trendDirection="up"
          detail="All 8 monitors active"
          icon={ShieldCheck}
          tone="emerald"
          values={[96, 98, 97, 99, 100, 99, 100, 100, 100]}
          sparklineId="health"
        />
      </div>

      <section id="scan" className="mt-5 scroll-mt-24">
        <Scanner variant="panel" />
      </section>

      <div className="mt-7 grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_356px]">
        <section id="competitors" className="scroll-mt-24">
          <div className="flex items-end justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-[15px] font-semibold tracking-tight text-ink">
                  Tracked competitors
                </h2>
                <span className="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[8px] font-semibold text-slate-500">
                  8 active
                </span>
              </div>
              <p className="mt-1 text-[10px] text-slate-400">
                Ranked by recent movement across your market
              </p>
            </div>
            <Link
              href="/dashboard/compare"
              className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-500 transition hover:text-indigo-600"
            >
              Compare all
              <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="mt-3.5 grid gap-3 sm:grid-cols-2">
            {competitors.map((competitor) => (
              <CompetitorCard key={competitor.id} competitor={competitor} />
            ))}
          </div>
        </section>

        <SignalFeed />
      </div>
    </div>
  );
}
