import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  CircleDashed,
  Clock3,
  Compass,
  FileWarning,
  Layers3,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
} from "lucide-react";
import { SiteHeader } from "@/components/marketing/site-header";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Scanner } from "@/components/scanner";
import { ProductPreview } from "@/components/marketing/product-preview";
import { Capabilities } from "@/components/marketing/capabilities";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Autonomous Market & Competitor Intelligence",
  description:
    "Nexus Intel continuously discovers competitor price changes, product launches, and off-site mentions — then turns them into structured intelligence your team can act on.",
};

const trustedNames = [
  { name: "NORTHSTAR", className: "font-semibold tracking-[0.16em]" },
  { name: "Fable", className: "font-semibold tracking-[-0.04em] text-[16px]" },
  { name: "MERIDIAN", className: "font-medium tracking-[0.2em]" },
  { name: "Arc", className: "font-semibold tracking-[-0.06em] text-[17px]" },
  { name: "clearscope", className: "font-medium tracking-[-0.02em]" },
  { name: "OPAL", className: "font-semibold tracking-[0.22em]" },
];

const solutions = [
  {
    icon: TrendingUp,
    label: "Revenue",
    title: "Walk into every deal with the latest move.",
    description:
      "Live battlecards, pricing comparisons, and objection-ready context for every competitive conversation.",
    points: ["Rep-ready Slack alerts", "CRM battlecards", "Pricing objection library"],
    tone: "indigo",
  },
  {
    icon: Layers3,
    label: "Product",
    title: "See what shipped before your roadmap review.",
    description:
      "Track competitor launches, packaging shifts, and feature gaps without another folder of screenshots.",
    points: ["Launch timelines", "Feature gap analysis", "Packaging shifts"],
    tone: "cyan",
  },
  {
    icon: Compass,
    label: "Strategy",
    title: "Turn scattered signals into board-ready context.",
    description:
      "A continuously refreshed view of the market, with the evidence trail your leadership team expects.",
    points: ["Executive briefs", "Market positioning maps", "Auditable source trail"],
    tone: "emerald",
  },
];

export default function MarketingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#F8FAFC]">
      <SiteHeader />

      <main>
        <section className="relative pb-16 pt-14 sm:pb-20 sm:pt-20">
          <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[860px] overflow-hidden">
            <div className="absolute left-1/2 top-[-330px] h-[620px] w-[980px] -translate-x-1/2 rounded-full bg-indigo-200/35 blur-[130px]" />
            <div className="absolute left-[6%] top-[300px] h-80 w-80 rounded-full bg-cyan-200/25 blur-[100px]" />
            <div className="absolute right-[4%] top-[210px] h-72 w-72 rounded-full bg-violet-200/30 blur-[100px]" />
            <div className="absolute inset-0 bg-dot-grid opacity-[0.22] [mask-image:linear-gradient(to_bottom,black_15%,transparent_78%)]" />
          </div>

          <div className="page-shell">
            <div className="mx-auto flex max-w-4xl flex-col items-center text-center">
              <Link
                href="#capabilities"
                className="group inline-flex items-center gap-2 rounded-full border border-slate-200/90 bg-white/80 py-1 pl-1 pr-3 text-[11px] text-slate-600 shadow-sm backdrop-blur transition hover:border-indigo-200 hover:bg-white"
              >
                <span className="rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.12em] text-white">
                  New
                </span>
                <span className="font-medium">Autonomous Scanning Engine</span>
                <ArrowRight className="h-3 w-3 text-slate-400 transition-transform group-hover:translate-x-0.5" />
              </Link>

              <h1 className="mt-6 text-balance text-[42px] font-semibold leading-[1.04] tracking-[-0.05em] text-ink sm:text-[58px] lg:text-[72px]">
                Autonomous Market &<br />
                <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-cyan-500 bg-clip-text text-transparent">
                  Competitor Intelligence
                </span>
              </h1>

              <p className="mt-6 max-w-[660px] text-pretty text-[15px] leading-[1.75] text-slate-500 sm:text-[17px]">
                One missed price change can cost you a deal. Your competitors never stop
                moving. <span className="font-medium text-slate-700">Now neither do you.</span>
              </p>

              <div className="mt-9 w-full max-w-[780px]">
                <Scanner />
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-[10px] text-slate-400">
                <span className="inline-flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                  Read-only by design
                </span>
                <span className="h-3 w-px bg-slate-200" />
                <span className="inline-flex items-center gap-1.5">
                  <Clock3 className="h-3.5 w-3.5 text-indigo-400" />
                  15-minute refresh
                </span>
                <span className="h-3 w-px bg-slate-200" />
                <span>No credit card required</span>
              </div>
            </div>

            <div className="mt-14 sm:mt-16">
              <p className="text-center text-[10px] font-medium uppercase tracking-[0.2em] text-slate-400">
                Built for market teams at
              </p>
              <div className="mx-auto mt-5 flex max-w-3xl flex-wrap items-center justify-center gap-x-9 gap-y-4 text-slate-400 sm:gap-x-12">
                {trustedNames.map((brand) => (
                  <span
                    key={brand.name}
                    className={cn("text-[13px] transition-colors hover:text-slate-500", brand.className)}
                  >
                    {brand.name}
                  </span>
                ))}
              </div>
            </div>

            <div id="product" className="scroll-mt-24">
              <ProductPreview />
            </div>
          </div>
        </section>

        <section className="border-t border-slate-200/70 bg-white/60 py-20 backdrop-blur-sm sm:py-28">
          <div className="page-shell">
            <div className="mx-auto max-w-2xl text-center">
              <p className="eyebrow">The status quo</p>
              <h2 className="mt-4 text-balance text-3xl font-semibold leading-[1.14] tracking-[-0.035em] text-ink sm:text-[42px]">
                Your market updates daily. Your intelligence shouldn&apos;t wait for Friday.
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-[14px] leading-relaxed text-slate-500">
                Competitive research was never meant to live in a quarterly slide deck. The
                companies that win are the ones that notice first.
              </p>
            </div>

            <div className="mt-12 grid gap-4 lg:grid-cols-2">
              <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-6 shadow-card sm:p-8">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
                    Manual tracking
                  </span>
                  <FileWarning className="h-4 w-4 text-slate-300" />
                </div>
                <h3 className="mt-6 max-w-sm text-[21px] font-semibold leading-snug tracking-[-0.025em] text-slate-700">
                  A folder of screenshots is not intelligence.
                </h3>
                <p className="mt-2 max-w-md text-[13px] leading-relaxed text-slate-500">
                  Someone remembers to check the pricing page. Someone else has a tab open.
                  And the update that mattered slips through on a busy Tuesday.
                </p>

                <div className="mt-7 space-y-3 border-t border-slate-100 pt-6">
                  {[
                    "Pricing pages change without a notification",
                    "Release notes are buried three clicks deep",
                    "Off-site mentions live in six different places",
                    "The weekly update is stale before it ships",
                  ].map((item) => (
                    <div key={item} className="flex items-center gap-3">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                        <X className="h-2.5 w-2.5" strokeWidth={2.5} />
                      </span>
                      <span className="text-[12px] text-slate-500">{item}</span>
                    </div>
                  ))}
                </div>

                <div className="mt-7 flex items-center gap-3 rounded-xl border border-slate-200/70 bg-slate-50/70 p-3">
                  <div className="flex -space-x-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-slate-200 text-[8px] font-semibold text-slate-500">
                      JL
                    </span>
                    <span className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-slate-300 text-[8px] font-semibold text-slate-600">
                      MK
                    </span>
                    <span className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-slate-100 text-[9px] text-slate-400">
                      +3
                    </span>
                  </div>
                  <p className="text-[10px] leading-relaxed text-slate-400">
                    Three people. Six browser tabs. Still no single source of truth.
                  </p>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 via-white to-cyan-50/60 p-6 shadow-[0_20px_60px_-30px_rgba(79,70,229,0.35)] sm:p-8">
                <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-indigo-200/30 blur-3xl" />
                <div className="relative flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-indigo-600">
                    <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-indigo-500" />
                    The Nexus way
                  </span>
                  <ScanSearch className="h-4 w-4 text-indigo-400" />
                </div>
                <h3 className="relative mt-6 max-w-sm text-[21px] font-semibold leading-snug tracking-[-0.025em] text-ink">
                  A living model of your market.
                </h3>
                <p className="relative mt-2 max-w-md text-[13px] leading-relaxed text-slate-500">
                  Nexus continuously resolves the public web into a structured, comparable
                  view of every competitor — and tells you what changed.
                </p>

                <div className="relative mt-7 space-y-3 border-t border-indigo-100/80 pt-6">
                  {[
                    "Every price, plan, and package change captured",
                    "Off-site news and launches connected to the source",
                    "Feature matrices updated without a manual touch",
                    "Executive briefs written the moment it matters",
                  ].map((item) => (
                    <div key={item} className="flex items-center gap-3">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100">
                        <Check className="h-2.5 w-2.5" strokeWidth={3} />
                      </span>
                      <span className="text-[12px] text-slate-600">{item}</span>
                    </div>
                  ))}
                </div>

                <div className="relative mt-7 rounded-xl border border-white bg-white/90 p-3.5 shadow-sm backdrop-blur">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                        <Sparkles className="h-3.5 w-3.5" />
                      </span>
                      <div>
                        <p className="text-[11px] font-semibold text-slate-800">
                          Price movement detected
                        </p>
                        <p className="mt-0.5 text-[10px] text-slate-500">
                          Trackline Pro · $119 → $99
                        </p>
                      </div>
                    </div>
                    <span className="rounded-full border border-emerald-100 bg-emerald-50 px-2 py-1 text-[8px] font-semibold uppercase tracking-[0.1em] text-emerald-700">
                      High impact
                    </span>
                  </div>
                  <div className="mt-3 flex items-center gap-2 border-t border-slate-100 pt-2.5">
                    <span className="text-[9px] text-slate-400">Brief generated</span>
                    <span className="h-px flex-1 bg-slate-100" />
                    <span className="font-mono text-[8px] text-indigo-500">8 min ago</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-4 grid divide-y divide-slate-200/70 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card sm:grid-cols-3 sm:divide-x sm:divide-y-0">
              {[
                {
                  icon: CircleDashed,
                  label: "Continuous",
                  text: "No manual triggers. Every surface, revisited.",
                },
                {
                  icon: Layers3,
                  label: "Structured",
                  text: "Not screenshots. A queryable market schema.",
                },
                {
                  icon: Sparkles,
                  label: "Decision-ready",
                  text: "Executive briefs, not raw change logs.",
                },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} className="flex items-start gap-3.5 p-5 sm:p-6">
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-indigo-500">
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <div>
                      <p className="text-[12px] font-semibold text-slate-800">{item.label}</p>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{item.text}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <Capabilities />

        <section
          id="solutions"
          className="relative border-y border-slate-200/70 bg-white py-20 sm:py-28"
        >
          <div className="page-shell">
            <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-end">
              <div>
                <p className="eyebrow">Solutions</p>
                <h2 className="mt-4 max-w-lg text-balance text-3xl font-semibold leading-[1.14] tracking-[-0.035em] text-ink sm:text-[42px]">
                  Built for the people who feel the market first.
                </h2>
              </div>
              <div className="lg:pb-1">
                <p className="max-w-lg text-[14px] leading-relaxed text-slate-500">
                  One live source of truth, shaped for the way each team works. From the
                  morning standup to the quarterly board review.
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-medium text-slate-500">
                    No manual research
                  </span>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-medium text-slate-500">
                    Shared across teams
                  </span>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-medium text-slate-500">
                    Source-level evidence
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {solutions.map((solution) => {
                const Icon = solution.icon;
                return (
                  <article
                    key={solution.label}
                    className="group relative overflow-hidden rounded-2xl border border-slate-200/80 bg-[#FBFCFE] p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white hover:shadow-card-hover"
                  >
                    <div
                      className={cn(
                        "absolute inset-x-0 top-0 h-[2px]",
                        solution.tone === "indigo" &&
                          "bg-gradient-to-r from-indigo-500 to-violet-500",
                        solution.tone === "cyan" && "bg-gradient-to-r from-cyan-500 to-sky-500",
                        solution.tone === "emerald" &&
                          "bg-gradient-to-r from-emerald-500 to-teal-500",
                      )}
                    />
                    <div className="flex items-center justify-between">
                      <span
                        className={cn(
                          "flex h-9 w-9 items-center justify-center rounded-xl border",
                          solution.tone === "indigo" && "border-indigo-100 bg-indigo-50 text-indigo-600",
                          solution.tone === "cyan" && "border-cyan-100 bg-cyan-50 text-cyan-600",
                          solution.tone === "emerald" &&
                            "border-emerald-100 bg-emerald-50 text-emerald-600",
                        )}
                      >
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                        {solution.label}
                      </span>
                    </div>
                    <h3 className="mt-5 text-[18px] font-semibold leading-snug tracking-[-0.025em] text-ink">
                      {solution.title}
                    </h3>
                    <p className="mt-2 text-[12.5px] leading-relaxed text-slate-500">
                      {solution.description}
                    </p>
                    <div className="mt-5 flex flex-wrap gap-1.5">
                      {solution.points.map((point) => (
                        <span
                          key={point}
                          className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[9px] font-medium text-slate-500"
                        >
                          {point}
                        </span>
                      ))}
                    </div>
                    <Link
                      href="/dashboard"
                      className="mt-5 inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 transition-colors group-hover:text-indigo-600"
                    >
                      Explore the console
                      <ArrowUpRight className="h-3 w-3" />
                    </Link>
                  </article>
                );
              })}
            </div>

          </div>
        </section>

        <section className="relative overflow-hidden py-20 sm:py-24">
          <div className="pointer-events-none absolute inset-0 bg-dot-grid opacity-[0.22] [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
          <div className="page-shell relative">
            <div className="relative overflow-hidden rounded-[28px] bg-[#0B1120] px-6 py-16 text-center shadow-[0_40px_100px_-40px_rgba(30,27,75,0.65)] sm:px-12 sm:py-20">
              <div className="pointer-events-none absolute left-1/2 top-0 h-72 w-[680px] -translate-x-1/2 rounded-full bg-indigo-500/25 blur-[110px]" />
              <div className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full bg-cyan-500/10 blur-[80px]" />
              <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_80%)]" />

              <div className="relative flex flex-col items-center">
                <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-400 backdrop-blur">
                  <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-emerald-400" />
                  Nexus Signal · 24 / 7
                </span>
                <h2 className="mt-6 max-w-2xl text-balance text-[34px] font-semibold leading-[1.1] tracking-[-0.04em] text-white sm:text-[48px]">
                  Your competitors never stop moving.
                  <br />
                  <span className="bg-gradient-to-r from-indigo-300 via-violet-300 to-cyan-300 bg-clip-text text-transparent">
                    Now neither do you.
                  </span>
                </h2>
                <p className="mt-5 max-w-lg text-[13px] leading-relaxed text-slate-400 sm:text-[14px]">
                  Set your market once. Wake up to the changes that matter, already structured,
                  prioritized, and ready for your next move.
                </p>
                <div className="mt-8 flex flex-col items-stretch gap-2.5 sm:flex-row">
                  <Link
                    href="/dashboard"
                    className={cn(
                      buttonVariants({ variant: "secondary", size: "lg" }),
                      "border-transparent bg-white text-slate-900 hover:bg-slate-100",
                    )}
                  >
                    Launch Console
                    <ArrowUpRight className="h-4 w-4" />
                  </Link>
                  <Link
                    href="/dashboard/compare"
                    className={cn(
                      buttonVariants({ variant: "outline", size: "lg" }),
                      "border-white/15 bg-white/[0.03] text-white hover:border-white/25 hover:bg-white/[0.07] hover:text-white",
                    )}
                  >
                    View live demo
                  </Link>
                </div>
                <div className="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-[10px] text-slate-500">
                  <span className="inline-flex items-center gap-1.5">
                    <Check className="h-3 w-3 text-emerald-400" />
                    14-day trial
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Check className="h-3 w-3 text-emerald-400" />
                    No credit card
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Check className="h-3 w-3 text-emerald-400" />
                    SOC 2 Type II
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
