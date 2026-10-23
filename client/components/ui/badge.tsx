import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium leading-none tracking-wide",
  {
    variants: {
      variant: {
        default: "border-slate-200 bg-slate-50 text-slate-600",
        outline: "border-slate-200 bg-white text-slate-600",
        brand: "border-indigo-100 bg-indigo-50 text-indigo-700",
        success: "border-emerald-100 bg-emerald-50 text-emerald-700",
        warning: "border-amber-100 bg-amber-50 text-amber-700",
        danger: "border-rose-100 bg-rose-50 text-rose-700",
        info: "border-cyan-100 bg-cyan-50 text-cyan-700",
        high: "border-amber-200/80 bg-amber-50 text-amber-800",
        watching: "border-violet-100 bg-violet-50 text-violet-700",
        stable: "border-emerald-100 bg-emerald-50 text-emerald-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { badgeVariants };
