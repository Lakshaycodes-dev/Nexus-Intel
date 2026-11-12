import type { Accent } from "./types";

export const accents = {
  indigo: {
    gradient: "from-indigo-500 to-violet-500",
    solid: "bg-indigo-600",
    soft: "bg-indigo-50 border-indigo-100",
    text: "text-indigo-600",
    hex: "#6366F1",
  },
  cyan: {
    gradient: "from-cyan-500 to-sky-500",
    solid: "bg-cyan-600",
    soft: "bg-cyan-50 border-cyan-100",
    text: "text-cyan-700",
    hex: "#06B6D4",
  },
  emerald: {
    gradient: "from-emerald-500 to-teal-500",
    solid: "bg-emerald-600",
    soft: "bg-emerald-50 border-emerald-100",
    text: "text-emerald-700",
    hex: "#10B981",
  },
  violet: {
    gradient: "from-violet-500 to-purple-500",
    solid: "bg-violet-600",
    soft: "bg-violet-50 border-violet-100",
    text: "text-violet-700",
    hex: "#8B5CF6",
  },
  sky: {
    gradient: "from-sky-500 to-blue-500",
    solid: "bg-sky-600",
    soft: "bg-sky-50 border-sky-100",
    text: "text-sky-700",
    hex: "#0EA5E9",
  },
  amber: {
    gradient: "from-amber-400 to-orange-500",
    solid: "bg-amber-500",
    soft: "bg-amber-50 border-amber-100",
    text: "text-amber-700",
    hex: "#F59E0B",
  },
  rose: {
    gradient: "from-rose-500 to-pink-500",
    solid: "bg-rose-600",
    soft: "bg-rose-50 border-rose-100",
    text: "text-rose-700",
    hex: "#F43F5E",
  },
  teal: {
    gradient: "from-teal-500 to-cyan-500",
    solid: "bg-teal-600",
    soft: "bg-teal-50 border-teal-100",
    text: "text-teal-700",
    hex: "#14B8A6",
  },
} satisfies Record<string, Accent>;

const palette = Object.values(accents);

export function accentFor(seed: string): Accent {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  }
  return palette[hash % palette.length];
}
