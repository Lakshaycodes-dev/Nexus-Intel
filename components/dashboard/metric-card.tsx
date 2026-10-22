import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

type Tone = "indigo" | "amber" | "cyan" | "emerald";

interface MetricCardProps {
  label: string;
  value: string;
  trend: string;
  trendDirection: "up" | "down" | "flat";
  detail: string;
  icon: React.ElementType;
  tone: Tone;
  values: number[];
  sparklineId: string;
}

const toneStyles: Record<
  Tone,
  { icon: string; line: string; fillFrom: string; gradientId: string }
> = {
  indigo: {
    icon: "border-indigo-100 bg-indigo-50 text-indigo-600",
    line: "#6366F1",
    fillFrom: "rgba(99,102,241,0.22)",
    gradientId: "metric-indigo",
  },
  amber: {
    icon: "border-amber-100 bg-amber-50 text-amber-600",
    line: "#F59E0B",
    fillFrom: "rgba(245,158,11,0.18)",
    gradientId: "metric-amber",
  },
  cyan: {
    icon: "border-cyan-100 bg-cyan-50 text-cyan-600",
    line: "#06B6D4",
    fillFrom: "rgba(6,182,212,0.16)",
    gradientId: "metric-cyan",
  },
  emerald: {
    icon: "border-emerald-100 bg-emerald-50 text-emerald-600",
    line: "#10B981",
    fillFrom: "rgba(16,185,129,0.16)",
    gradientId: "metric-emerald",
  },
};

function buildPoints(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 100;
      const y = 32 - ((value - min) / range) * 25;
      return `${x},${y}`;
    })
    .join(" ");
}

export function MetricCard({
  label,
  value,
  trend,
  trendDirection,
  detail,
  icon: Icon,
  tone,
  values,
  sparklineId,
}: MetricCardProps) {
  const styles = toneStyles[tone];
  const points = buildPoints(values);
  const TrendIcon =
    trendDirection === "up" ? ArrowUpRight : trendDirection === "down" ? ArrowDownRight : Minus;

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card transition-shadow duration-300 hover:shadow-card-hover">
      <div className="relative z-10 flex items-start justify-between gap-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
          {label}
        </p>
        <span
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border",
            styles.icon,
          )}
        >
          <Icon className="h-3.5 w-3.5" />
        </span>
      </div>

      <div className="relative z-10 mt-3 flex items-baseline gap-2">
        <span className="text-[28px] font-semibold leading-none tracking-[-0.04em] text-ink">
          {value}
        </span>
        <span
          className={cn(
            "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-semibold",
            trendDirection === "up" && "bg-emerald-50 text-emerald-700",
            trendDirection === "down" && "bg-amber-50 text-amber-700",
            trendDirection === "flat" && "bg-slate-100 text-slate-500",
          )}
        >
          <TrendIcon className="h-2.5 w-2.5" />
          {trend}
        </span>
      </div>
      <p className="relative z-10 mt-2 text-[10px] text-slate-400">{detail}</p>

      <div className="pointer-events-none absolute bottom-0 right-0 h-[46px] w-[42%] opacity-80">
        <svg viewBox="0 0 100 36" preserveAspectRatio="none" className="h-full w-full">
          <defs>
            <linearGradient id={`${sparklineId}-fill`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={styles.fillFrom} />
              <stop offset="100%" stopColor="rgba(255,255,255,0)" />
            </linearGradient>
          </defs>
          <polygon points={`0,36 ${points} 100,36`} fill={`url(#${sparklineId}-fill)`} />
          <polyline
            points={points}
            fill="none"
            stroke={styles.line}
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </div>
    </div>
  );
}
