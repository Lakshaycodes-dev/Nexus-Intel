import type { ScopeKey } from "./types";

export const SCAN_SCOPES: { key: ScopeKey; label: string }[] = [
  { key: "pricing", label: "Pricing & Billing" },
  { key: "product", label: "Product Updates" },
  { key: "news", label: "News & Mentions" },
];

export const DEFAULT_SCOPES: Record<ScopeKey, boolean> = {
  pricing: true,
  product: true,
  news: true,
};

export const scanScopeLabels: Record<ScopeKey, string> = {
  pricing: "Pricing",
  product: "Product",
  news: "News",
};

export function scopeLabel(key: ScopeKey) {
  return SCAN_SCOPES.find((scope) => scope.key === key)?.label ?? key;
}
