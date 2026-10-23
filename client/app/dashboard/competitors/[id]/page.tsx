import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  Activity,
  ArrowUpRight,
  BadgeDollarSign,
  CalendarDays,
  CreditCard,
  ExternalLink,
  Gauge,
  Globe2,
  Layers3,
  MapPin,
  MessagesSquare,
  Newspaper,
  ShieldCheck,
  Sparkles,
  Tag,
  Users,
} from "lucide-react";
import { competitors, getCompetitor } from "@/lib/data";
import { cn, formatCurrency } from "@/lib/utils";
import { CompetitorHeader } from "@/components/dashboard/competitor-header";
import { PricingMatrix } from "@/components/dashboard/pricing-matrix";
import { FeatureAccordions } from "@/components/dashboard/feature-accordions";
import { MentionsFeed } from "@/components/dashboard/mentions-feed";
import { buttonVariants } from "@/components/ui/button";

interface CompetitorPageProps {
  params: Promise<{ id: string }>;
}

export function generateStaticParams() {
  return competitors.map((competitor) => ({ id: competitor.id }));
}

export async function generateMetadata({
  params,
}: CompetitorPageProps): Promise<Metadata> {
  const { id } = await params;
  const competitor = getCompetitor(id);

  if (!competitor) {
    return { title: "Competitor not found" };
  }

  return {
    title: `${competitor.name} — Intelligence Brief`,
    description: competitor.tagline,
  };
}

export default async function CompetitorPage({ params }: CompetitorPageProps) {
  const { id } = await params;
  const competitor = getCompetitor(id);

  if (!competitor) {
    notFound();
  }

  const breakdown = [
    {
      label: "Pricing velocity",
      value: Math.min(94, 48 + competitor.priceChanges * 12),
      color: "from-amber-400 to-orange-500",
    },
    {
      label: "Product velocity",
      value: Math.min(92, 46 + competitor.featureLaunches * 13),
      color: "from-indigo-500 to-violet-500",
    },
    {
      label: "Off-site presence",
      value: Math.min(90, 38 + competitor.mentions30d * 2),
      color: "from-cyan-400 to-sky-500",
    },
  ];

  const accountFacts = [
    { label: "Website", value: competitor.domain, icon: Globe2 },
    { label: "Headquarters", value: competitor.hq, icon: MapPin },
    { label: "Team size", value: `${competitor.employees} people`, icon: Users },
    { label: "Founded", value: competitor.founded, icon: CalendarDays },
    { label: "Category", value: competitor.category, icon: Tag },
    { label: "Pricing model", value: "Subscription + usage", icon: CreditCard },
  ];

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <CompetitorHeader competitor={competitor} />

      <div className="mt-3 grid grid-cols-2 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card sm:grid-cols-4 sm:divide-x sm:divide-slate-100">
        <div className="border-b border-slate-100 p-4 sm:border-b-0">
          <div className="flex items-center justify-between">
            <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-400">
              Starting tier
            </p>
            <BadgeDollarSign className="h-3.5 w-3.5 text-slate-300" />
          </div>
          <p className="mt-2 text-[20px] font-semibold tracking-[-0.03em] text-ink">
            {formatCurrency(competitor.startingPrice)}
            <span className="ml-1 text-[10px] font-normal text-slate-400">/ mo</span>
          </p>
          <p className="mt-0.5 text-[9px] text-slate-400">Starter · monthly billing</p>
        </div>

        <div className="border-b border-slate-100 p-4 sm:border-b-0">
          <div className="flex items-center justify-between">
            <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-400">
              Pro tier
            </p>
            <Layers3 className="h-3.5 w-3.5 text-slate-300" />
          </div>
          <p className="mt-2 text-[20px] font-semibold tracking-[-0.03em] text-ink">
            {formatCurrency(competitor.proPrice)}
            <span className="ml-1 text-[10px] font-normal text-slate-400">/ mo</span>
          </p>
          <p className="mt-0.5 text-[9px] text-slate-400">
            {competitor.priceChanges > 0 ? "Changed this cycle" : "No change this cycle"}
          </p>
        </div>

        <div className="border-b border-slate-100 p-4 sm:border-b-0">
          <div className="flex items-center justify-between">
            <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-400">
              Movement score
            </p>
            <Activity className="h-3.5 w-3.5 text-slate-300" />
          </div>
          <p className="mt-2 text-[20px] font-semibold tracking-[-0.03em] text-ink">
            {competitor.movementScore}
            <span className="ml-1 text-[10px] font-normal text-slate-400">/ 100</span>
          </p>
          <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500"
              style={{ width: `${competitor.movementScore}%` }}
            />
          </div>
        </div>

        <div className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-400">
              Mentions · 30d
            </p>
            <Newspaper className="h-3.5 w-3.5 text-slate-300" />
          </div>
          <p className="mt-2 text-[20px] font-semibold tracking-[-0.03em] text-ink">
            {competitor.mentions30d}
            <span className="ml-1 text-[10px] font-normal text-slate-400">signals</span>
          </p>
          <p className="mt-0.5 text-[9px] text-slate-400">Across 6 public sources</p>
        </div>
      </div>

      <div className="mt-4 grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_336px]">
        <div className="space-y-4">
          <section className="print-avoid-break relative overflow-hidden rounded-2xl border border-indigo-100/80 bg-white shadow-card">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-indigo-50/80 via-indigo-50/20 to-transparent" />
            <div className="relative p-5 sm:p-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-[0_8px_18px_-8px_rgba(99,102,241,0.7)]">
                    <Sparkles className="h-4 w-4" />
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-[15px] font-semibold tracking-tight text-ink">
                        AI executive summary
                      </h2>
                      <span className="rounded-full border border-indigo-100 bg-white px-2 py-0.5 text-[8px] font-semibold uppercase tracking-[0.1em] text-indigo-600">
                        Nexus analysis
                      </span>
                    </div>
                    <p className="mt-1 text-[10px] text-slate-400">
                      Generated from the latest scan · 8 min ago
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1.5 rounded-full border border-emerald-100 bg-emerald-50/80 px-2.5 py-1 text-[9px] font-medium text-emerald-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    {competitor.confidence}% confidence
                  </span>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {competitor.summary.map((insight, index) => (
                  <div
                    key={insight}
                    className="flex gap-3.5 rounded-xl border border-slate-200/70 bg-white/80 px-4 py-3.5 shadow-[0_1px_1px_rgba(15,23,42,0.02)] backdrop-blur-sm"
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-indigo-50 font-mono text-[8px] font-semibold text-indigo-500">
                      0{index + 1}
                    </span>
                    <p className="text-[11.5px] leading-relaxed text-slate-600">{insight}</p>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex flex-col gap-2 border-t border-slate-100 pt-3.5 sm:flex-row sm:items-center sm:justify-between">
                <span className="flex items-center gap-1.5 text-[9px] text-slate-400">
                  <ShieldCheck className="h-3 w-3 text-emerald-500" />
                  Based on 14 pages and {competitor.mentions30d} off-site mentions
                </span>
                <Link
                  href="#mentions"
                  className="inline-flex items-center gap-1 text-[9px] font-semibold text-indigo-600 transition hover:text-indigo-800"
                >
                  Review evidence trail
                  <ArrowUpRight className="h-2.5 w-2.5" />
                </Link>
              </div>
            </div>
          </section>

          <PricingMatrix competitor={competitor} />

          <FeatureAccordions groups={competitor.featureGroups} />

          <MentionsFeed mentions={competitor.mentions} />
        </div>

        <aside className="space-y-4">
          <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="text-[13px] font-semibold text-ink">Account snapshot</h2>
                <p className="mt-0.5 text-[9px] text-slate-400">Public company profile</p>
              </div>
              <a
                href={`https://${competitor.domain}`}
                target="_blank"
                rel="noreferrer"
                aria-label={`Open ${competitor.domain}`}
                className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 text-slate-400 transition hover:text-indigo-600"
              >
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <div className="divide-y divide-slate-100 px-5">
              {accountFacts.map((fact) => {
                const Icon = fact.icon;
                return (
                  <div key={fact.label} className="flex items-center gap-3 py-3">
                    <Icon className="h-3.5 w-3.5 shrink-0 text-slate-300" />
                    <span className="text-[10px] text-slate-400">{fact.label}</span>
                    <span className="ml-auto max-w-[150px] truncate text-right text-[10px] font-medium text-slate-600">
                      {fact.value}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-3">
              <div className="flex items-center justify-between text-[9px]">
                <span className="flex items-center gap-1.5 text-slate-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  Monitor active
                </span>
                <span className="font-mono text-slate-400">{competitor.lastScan}</span>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-[13px] font-semibold text-ink">Movement profile</h2>
                <p className="mt-0.5 text-[9px] text-slate-400">Relative to your market</p>
              </div>
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-100 bg-slate-50 text-slate-500">
                <Gauge className="h-3.5 w-3.5" />
              </span>
            </div>
            <div className="mt-4 flex items-end gap-2">
              <span className="text-[28px] font-semibold leading-none tracking-[-0.04em] text-ink">
                {competitor.movementScore}
              </span>
              <span className="pb-0.5 text-[10px] text-slate-400">/ 100 overall</span>
            </div>
            <div className="mt-4 space-y-3">
              {breakdown.map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between text-[9px]">
                    <span className="text-slate-500">{item.label}</span>
                    <span className="font-mono text-slate-400">{item.value}</span>
                  </div>
                  <div className="mt-1 h-1 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={cn("h-full rounded-full bg-gradient-to-r", item.color)}
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-100 bg-amber-50/60 px-2.5 py-2">
              <Activity className="h-3 w-3 shrink-0 text-amber-600" />
              <p className="text-[9px] leading-relaxed text-amber-800">
                Above-average movement in pricing. Worth a weekly review.
              </p>
            </div>
          </section>

          <section className="print-avoid-break relative overflow-hidden rounded-2xl bg-[#0B1120] p-5 text-white shadow-[0_20px_50px_-24px_rgba(15,23,42,0.55)]">
            <div className="pointer-events-none absolute -right-14 -top-14 h-44 w-44 rounded-full bg-indigo-500/25 blur-3xl" />
            <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:28px_28px] [mask-image:radial-gradient(ellipse_at_top_right,black,transparent_75%)]" />
            <div className="relative">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.05] px-2 py-1 text-[8px] font-semibold uppercase tracking-[0.13em] text-cyan-300">
                <Sparkles className="h-2.5 w-2.5" />
                Recommended next move
              </span>
              <h2 className="mt-3 text-[15px] font-semibold tracking-tight text-white">
                Protect the mid-market narrative.
              </h2>
              <p className="mt-2 text-[10.5px] leading-relaxed text-slate-400">
                {competitor.summary[competitor.summary.length - 1]}
              </p>
              <Link
                href="/dashboard/compare"
                className={cn(
                  buttonVariants({ variant: "secondary", size: "sm" }),
                  "mt-4 w-full border-transparent bg-white text-slate-900 hover:bg-slate-100",
                )}
              >
                Open comparison matrix
                <ArrowUpRight className="h-3 w-3" />
              </Link>
              <div className="mt-3 flex items-center justify-between text-[8px] text-slate-500">
                <span className="flex items-center gap-1">
                  <MessagesSquare className="h-2.5 w-2.5" />
                  Based on {competitor.mentions30d} signals
                </span>
                <span>Updated 8m ago</span>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
