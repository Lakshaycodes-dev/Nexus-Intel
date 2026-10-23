import type { Config } from "tailwindcss";
import forms from "@tailwindcss/forms";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0F172A",
          soft: "#1E293B",
        },
        canvas: "#F7F8FC",
        brand: {
          50: "#EEF2FF",
          100: "#E0E7FF",
          200: "#C7D2FE",
          300: "#A5B4FC",
          400: "#818CF8",
          500: "#6366F1",
          600: "#4F46E5",
          700: "#4338CA",
          800: "#3730A3",
          900: "#312E81",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px -12px rgba(15, 23, 42, 0.10)",
        "card-hover":
          "0 2px 4px rgba(15, 23, 42, 0.04), 0 18px 40px -18px rgba(15, 23, 42, 0.18)",
        float:
          "0 30px 80px -28px rgba(30, 41, 59, 0.25), 0 2px 8px rgba(15, 23, 42, 0.04)",
        glow: "0 0 0 1px rgba(99, 102, 241, 0.12), 0 16px 48px -12px rgba(99, 102, 241, 0.35)",
      },
      backgroundImage: {
        "dot-grid":
          "radial-gradient(circle at 1px 1px, rgba(100, 116, 139, 0.16) 1px, transparent 0)",
        "hero-glow":
          "radial-gradient(ellipse 70% 60% at 50% 0%, rgba(224, 231, 255, 0.9), transparent 70%)",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.55", transform: "scale(0.94)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        scan: {
          "0%": { transform: "translateY(-10%)", opacity: "0" },
          "12%": { opacity: "0.85" },
          "88%": { opacity: "0.85" },
          "100%": { transform: "translateY(1000%)", opacity: "0" },
        },
        blink: {
          "0%, 49%": { opacity: "1" },
          "50%, 100%": { opacity: "0" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-soft": "pulse-soft 2.4s ease-in-out infinite",
        marquee: "marquee 32s linear infinite",
        scan: "scan 4.5s ease-in-out infinite",
        blink: "blink 1.1s step-end infinite",
        "fade-up": "fade-up 0.6s ease-out both",
      },
    },
  },
  plugins: [forms],
};

export default config;
