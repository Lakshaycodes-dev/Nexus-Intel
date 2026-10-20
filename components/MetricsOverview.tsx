import { ArrowUpRight, Layers3, ShieldCheck, Sparkles, Zap } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  description: string;
  chip: string;
  icon: typeof Zap;
  iconClass: string;
  glowClass: string;
  valueClass?: string;
  children: React.ReactNode;
}

function MetricCard({
  label,
  value,
  unit,
  description,
  chip,
  icon: Icon,
  iconClass,
  glowClass,
  valueClass = "text-white",
  children,
}: MetricCardProps) {
  return (
    <div className="card-sheen group relative overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.045] to-white/[0.012] p-5 shadow-card transition-all duration-300 hover:-translate-y-0.5 hover:border-white/[0.14]">
      <div
        className={`pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full blur-3xl ${glowClass}`}
      />
      <div className="relative">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`flex h-8 w-8 items-center justify-center rounded-lg border ${iconClass}`}
            >
              <Icon className="h-4 w-4" strokeWidth={1.9} />
            </span>
            <span className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-slate-500">
              {label}
            </span>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full border border-white/[0.07] bg-white/[0.02] px-1.5 py-0.5 text-[9px] font-medium text-slate-500">
            {chip}
            <ArrowUpRight className="h-2.5 w-2.5 opacity-60" />
          </span>
        </div>

        <div className="mt-4 flex items-baseline gap-1.5">
          <span
            className={`text-[clamp(22px,2.4vw,30px)] font-semibold leading-none tracking-tight ${valueClass}`}
          >
            {value}
          </span>
          {unit && (
            <span className="text-xs font-medium text-slate-500">{unit}</span>
          )}
        </div>

        <p className="mt-2 min-h-[36px] text-[11.5px] leading-relaxed text-slate-400">
          {description}
        </p>

        <div className="mt-4 border-t border-white/[0.05] pt-3">{children}</div>
      </div>
    </div>
  );
}

export default function MetricsOverview() {
  return (
    <section aria-labelledby="metrics-heading">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-indigo-300/70">
            Operating leverage
          </p>
          <h2
            id="metrics-heading"
            className="mt-1 text-base font-semibold tracking-tight text-white"
          >
            Why autonomous intelligence wins
          </h2>
        </div>
        <span className="chip border-indigo-400/15 bg-indigo-500/[0.05] text-indigo-200/70">
          <Sparkles className="h-3 w-3" />
          Benchmark · Hackathon build
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard
          label="Efficiency Gain"
          value="~480×"
          unit="faster"
          description="4 hours of analyst research compressed into a single 30-second autonomous run."
          chip="vs. manual"
          icon={Zap}
          iconClass="border-amber-400/20 bg-amber-400/[0.09] text-amber-300"
          glowClass="bg-amber-400/[0.09]"
        >
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[9.5px]">
              <span className="text-slate-500">Analyst workflow</span>
              <span className="font-mono text-slate-500">4 hrs</span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-white/[0.06]">
              <div className="h-full w-full rounded-full bg-slate-600/60" />
            </div>
            <div className="flex items-center justify-between text-[9.5px]">
              <span className="text-slate-400">Nexus Intel agent</span>
              <span className="font-mono text-indigo-300">30s</span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-white/[0.06]">
              <div className="h-full w-[14%] rounded-full bg-gradient-to-r from-indigo-400 to-cyan-300 shadow-[0_0_12px_rgba(99,102,241,0.8)]" />
            </div>
          </div>
        </MetricCard>

        <MetricCard
          label="Data Coverage"
          value="100%"
          unit="dynamic"
          description="JS-rendered DOM, hidden accordions and off-site signals captured with zero blind spots."
          chip="vs. static"
          icon={Layers3}
          iconClass="border-cyan-400/20 bg-cyan-400/[0.08] text-cyan-300"
          glowClass="bg-cyan-400/[0.08]"
        >
          <div className="flex flex-wrap gap-1">
            {["JS DOM", "Hidden toggles", "Press", "Reddit"].map((source) => (
              <span
                key={source}
                className="rounded-md border border-white/[0.06] bg-white/[0.025] px-1.5 py-0.5 font-mono text-[9px] text-slate-400"
              >
                {source}
              </span>
            ))}
            <span className="ml-auto font-mono text-[9px] text-emerald-300/80">
              4/4 surfaces
            </span>
          </div>
        </MetricCard>

        <MetricCard
          label="Extraction Accuracy"
          value="Deterministic"
          unit="JSON"
          description="Gemini 1.5 Flash constrained by Pydantic into a stable, schema-validated contract."
          chip="0 drift"
          icon={ShieldCheck}
          iconClass="border-emerald-400/20 bg-emerald-400/[0.08] text-emerald-300"
          glowClass="bg-emerald-400/[0.08]"
          valueClass="text-gradient-accent"
        >
          <div className="flex items-center justify-between gap-2 rounded-md border border-white/[0.05] bg-ink-950/60 px-2 py-1.5 font-mono text-[9px] leading-tight">
            <span className="text-slate-500">
              <span className="text-indigo-300">{"{"}</span> schema:{" "}
              <span className="text-emerald-300">&quot;valid&quot;</span>, drift:{" "}
              <span className="text-emerald-300">0</span>
              <span className="text-indigo-300">{"}"}</span>
            </span>
            <span className="shrink-0 rounded bg-emerald-400/10 px-1 py-0.5 text-emerald-300/90">
              Pydantic
            </span>
          </div>
        </MetricCard>
      </div>
    </section>
  );
}
