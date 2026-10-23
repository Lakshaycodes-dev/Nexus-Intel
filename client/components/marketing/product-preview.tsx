import Image from "next/image";
import {
  ArrowUpRight,
  BarChart3,
  Bell,
  Boxes,
  ChevronRight,
  CircleDot,
  Command,
  Compass,
  LayoutDashboard,
  LineChart,
  Radar,
  Settings,
  Sparkles,
} from "lucide-react";
import { competitors, marketSignals } from "@/lib/data";

const nav = [
  { label: "Overview", icon: LayoutDashboard, active: true },
  { label: "Competitors", icon: Compass },
  { label: "Signals", icon: Radar },
  { label: "Comparison", icon: Boxes },
  { label: "Reports", icon: BarChart3 },
];

const previewCompetitors = competitors.slice(0, 3);

export function ProductPreview() {
  return (
    <div className="relative mx-auto mt-16 max-w-[1120px] sm:mt-20">
      <div className="pointer-events-none absolute -inset-x-8 top-10 -z-10 h-64 rounded-[60px] bg-gradient-to-r from-indigo-200/35 via-violet-200/30 to-cyan-200/35 blur-3xl" />
      <div className="rounded-[26px] border border-white/90 bg-white/70 p-1.5 shadow-[0_50px_120px_-42px_rgba(30,41,59,0.32),0_2px_10px_rgba(15,23,42,0.05)] backdrop-blur sm:p-2">
        <div className="overflow-hidden rounded-[20px] border border-slate-200/90 bg-[#F7F8FC]">
          <div className="flex h-9 items-center justify-between border-b border-slate-200/80 bg-white px-3.5">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[#FDA4AF]" />
              <span className="h-2 w-2 rounded-full bg-[#FCD34D]" />
              <span className="h-2 w-2 rounded-full bg-[#6EE7B7]" />
            </div>
            <div className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-3 py-0.5 font-mono text-[8px] text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              app.nexusintel.ai / overview
            </div>
            <div className="flex items-center gap-1 text-[8px] font-semibold uppercase tracking-[0.16em] text-slate-400">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-emerald-500" />
              Live
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-[156px_1fr]">
            <div className="hidden border-r border-slate-200/80 bg-white/80 p-2.5 md:block">
              <div className="flex items-center px-1.5 py-2">
                <Image
                  src="/nexus-intel-logo.png"
                  alt="Nexus Intel"
                  width={980}
                  height={254}
                  className="h-5 w-auto object-contain"
                />
              </div>

              <div className="mb-3 mt-2 flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50/80 px-2 py-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="flex h-4 w-4 items-center justify-center rounded bg-slate-900 text-[7px] font-semibold text-white">
                    A
                  </span>
                  <span className="text-[8px] font-medium text-slate-600">Acme Corp</span>
                </div>
                <span className="text-[8px] text-slate-400">⌄</span>
              </div>

              <p className="mb-1 px-2 text-[6.5px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                Workspace
              </p>
              <div className="space-y-0.5">
                {nav.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div
                      key={item.label}
                      className={
                        item.active
                          ? "flex items-center gap-2 rounded-md bg-indigo-50 px-2 py-1.5 text-[8px] font-medium text-indigo-700"
                          : "flex items-center gap-2 rounded-md px-2 py-1.5 text-[8px] text-slate-500"
                      }
                    >
                      <Icon className="h-2.5 w-2.5" />
                      {item.label}
                    </div>
                  );
                })}
              </div>

              <p className="mb-1 mt-5 px-2 text-[6.5px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                Manage
              </p>
              <div className="flex items-center gap-2 rounded-md px-2 py-1.5 text-[8px] text-slate-500">
                <Settings className="h-2.5 w-2.5" />
                Settings
              </div>

              <div className="mt-8 rounded-lg border border-indigo-100 bg-gradient-to-b from-indigo-50 to-white p-2.5">
                <Sparkles className="h-3 w-3 text-indigo-500" />
                <p className="mt-1.5 text-[8px] font-semibold text-slate-800">Signal coverage</p>
                <p className="mt-0.5 text-[7px] leading-relaxed text-slate-500">
                  12 new mentions across 8 competitors.
                </p>
                <div className="mt-2 h-1 overflow-hidden rounded-full bg-indigo-100">
                  <div className="h-full w-[78%] rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400" />
                </div>
              </div>
            </div>

            <div className="min-w-0 p-3.5 sm:p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-1.5">
                    <p className="text-[7px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                      Wednesday, October 21
                    </p>
                    <span className="rounded bg-emerald-50 px-1 py-0.5 text-[6px] font-semibold uppercase tracking-wide text-emerald-600">
                      Live
                    </span>
                  </div>
                  <h3 className="mt-1 text-[15px] font-semibold tracking-tight text-slate-900 sm:text-[17px]">
                    Market overview
                  </h3>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="hidden items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-[7.5px] text-slate-500 sm:flex">
                    <Command className="h-2.5 w-2.5" />
                    Search
                  </span>
                  <span className="flex h-6 w-6 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500">
                    <Bell className="h-2.5 w-2.5" />
                  </span>
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-cyan-400 text-[7px] font-semibold text-white">
                    AL
                  </span>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-2">
                {[
                  { label: "Tracked", value: "8", trend: "2 added", icon: Compass },
                  { label: "Price changes", value: "3", trend: "+3 this week", icon: LineChart },
                  { label: "Feature launches", value: "5", trend: "4 new today", icon: Sparkles },
                ].map((metric) => {
                  const Icon = metric.icon;
                  return (
                    <div
                      key={metric.label}
                      className="rounded-lg border border-slate-200/80 bg-white p-2.5 shadow-sm"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[7px] font-medium uppercase tracking-wide text-slate-400">
                          {metric.label}
                        </span>
                        <Icon className="h-2.5 w-2.5 text-indigo-400" />
                      </div>
                      <p className="mt-1 text-[16px] font-semibold tracking-tight text-slate-900">
                        {metric.value}
                      </p>
                      <p className="mt-0.5 text-[6.5px] text-emerald-600">{metric.trend}</p>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-[1.25fr_1fr]">
                <div className="rounded-lg border border-slate-200/80 bg-white p-3 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[8.5px] font-semibold text-slate-800">Competitor movement</p>
                      <p className="mt-0.5 text-[6.5px] text-slate-400">Ranked by signal velocity</p>
                    </div>
                    <span className="flex items-center gap-1 text-[6.5px] font-medium text-indigo-600">
                      View all <ArrowUpRight className="h-2 w-2" />
                    </span>
                  </div>
                  <div className="mt-2.5 space-y-1.5">
                    {previewCompetitors.map((competitor, index) => (
                      <div
                        key={competitor.id}
                        className="flex items-center gap-2 rounded-md border border-slate-100 bg-slate-50/50 px-2 py-1.5"
                      >
                        <span
                          className={`flex h-5 w-5 items-center justify-center rounded-md bg-gradient-to-br ${competitor.accent.gradient} text-[6.5px] font-semibold text-white`}
                        >
                          {competitor.monogram}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-[8px] font-medium text-slate-700">{competitor.name}</p>
                          <p className="truncate text-[6.5px] text-slate-400">
                            {competitor.latestChange}
                          </p>
                        </div>
                        <div className="flex items-end gap-[2px]">
                          {[35, 48, 38, 62, 55, 78, 68, 88].map((height, barIndex) => (
                            <span
                              key={barIndex}
                              style={{ height: `${height / 6}px` }}
                              className={`w-[2px] rounded-full ${
                                barIndex > 5 ? "bg-indigo-500" : "bg-slate-200"
                              }`}
                            />
                          ))}
                        </div>
                        <span
                          className={`rounded px-1 py-0.5 text-[5.5px] font-semibold uppercase tracking-wide ${
                            index === 0
                              ? "bg-amber-50 text-amber-600"
                              : "bg-emerald-50 text-emerald-600"
                          }`}
                        >
                          {index === 0 ? "High" : "Stable"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200/80 bg-white p-3 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-[8.5px] font-semibold text-slate-800">Live signals</p>
                    <span className="flex items-center gap-1 text-[6px] font-semibold uppercase tracking-wide text-emerald-600">
                      <span className="h-1 w-1 rounded-full bg-emerald-500" />
                      Live
                    </span>
                  </div>
                  <div className="mt-2.5 space-y-2">
                    {marketSignals.slice(0, 3).map((signal) => (
                      <div key={signal.id} className="flex gap-1.5">
                        <CircleDot className="mt-0.5 h-2 w-2 shrink-0 text-indigo-400" />
                        <div className="min-w-0">
                          <p className="line-clamp-2 text-[7px] font-medium leading-snug text-slate-600">
                            {signal.title}
                          </p>
                          <p className="mt-0.5 text-[6px] text-slate-400">
                            {signal.competitor} · {signal.time}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <button className="mt-3 flex w-full items-center justify-center gap-1 rounded-md border border-slate-200 py-1 text-[6.5px] font-medium text-slate-500">
                    Open signal feed
                    <ChevronRight className="h-2 w-2" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="absolute -bottom-5 right-8 hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-2 text-[10px] font-medium text-slate-500 shadow-card sm:flex">
        <span className="h-1.5 w-1.5 rounded-full bg-cyan-500" />
        Every scan versioned and auditable
      </div>
    </div>
  );
}
