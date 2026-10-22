import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "border border-indigo-600/20 bg-gradient-to-b from-indigo-500 to-indigo-600 text-white shadow-[0_1px_2px_rgba(15,23,42,0.18),0_8px_20px_-8px_rgba(79,70,229,0.65)] hover:from-indigo-500 hover:to-indigo-700 hover:shadow-[0_1px_2px_rgba(15,23,42,0.18),0_12px_26px_-8px_rgba(79,70,229,0.7)] active:translate-y-px",
        secondary:
          "border border-slate-200 bg-white text-slate-700 shadow-sm hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900",
        outline:
          "border border-slate-300 bg-transparent text-slate-700 hover:border-slate-400 hover:bg-white hover:text-slate-900",
        ghost:
          "border border-transparent text-slate-600 hover:bg-slate-100/80 hover:text-slate-900",
        dark: "border border-slate-900 bg-slate-900 text-white shadow-sm hover:bg-slate-800",
        cyan:
          "border border-cyan-600/20 bg-gradient-to-b from-cyan-500 to-cyan-600 text-white shadow-[0_8px_20px_-8px_rgba(8,145,178,0.6)] hover:to-cyan-700",
        success:
          "border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
        link: "text-indigo-600 underline-offset-4 hover:underline",
      },
      size: {
        xs: "h-7 px-2.5 text-xs",
        sm: "h-9 px-4 text-[13px]",
        md: "h-10 px-5",
        lg: "h-12 px-6 text-[15px]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { Button };
