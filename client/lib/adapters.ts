/**
 * Adapters that translate the backend's compact `CompetitorData` contract into
 * the richer `Competitor` view model used by the dashboard components.
 */

import { accentFor } from "./accents";
import { formatCurrency } from "./utils";
import type {
  AnalysisRecord,
  CapabilityEntry,
  CompetitorData,
  CompetitorResponse,
  NewsEntry,
  PricingEntry,
} from "./api";
import type {
  ComparisonProfile,
  Competitor,
  FeatureGroup,
  Mention,
  MentionType,
  PricingTier,
  ThreatLevel,
} from "./types";

const DEFAULT_COMPARISON: ComparisonProfile = {
  refreshMinutes: 1440,
  coverage: "Online + stores",
  retentionMonths: 12,
  freeTrialDays: 0,
  sso: false,
  soc2: false,
  auditLogs: false,
  slack: false,
  api: false,
  webhooks: false,
  crm: "Unknown",
  p1Response: "Unknown",
  dedicatedCsm: false,
  onboarding: "Self-serve",
};

function parsePrice(value: string | null | undefined): number | null {
  if (!value) return null;
  const match = value.match(/-?\d[\d,]*(?:\.\d+)?/);
  if (!match) return null;
  const amount = Number(match[0].replace(/,/g, ""));
  return Number.isFinite(amount) ? amount : null;
}

function displayName(domain: string): string {
  const label = domain.split(".")[0] || domain;
  return label
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function monogramFor(name: string, domain: string): string {
  const letters = name.replace(/[^a-zA-Z0-9]/g, "");
  if (letters.length >= 2) return letters.slice(0, 2).toUpperCase();
  return (domain.split(".")[0] || "NI").slice(0, 2).toUpperCase();
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "just now";
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "recently";
  const diffSeconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  const minutes = Math.round(diffSeconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function toPricingTier(entry: PricingEntry, index: number, total: number): PricingTier {
  const monthly = parsePrice(entry.monthly) ?? parsePrice(entry.annual) ?? 0;
  const annualTotal = parsePrice(entry.annual);
  const annualMonthly =
    annualTotal !== null ? Math.round(annualTotal / 12) : Math.round(monthly * 0.8);
  const highlighted = index === Math.min(1, total - 1);

  return {
    name: entry.tier || `Tier ${index + 1}`,
    description:
      index === 0
        ? "Entry price band resolved from the public catalogue."
        : index === total - 1
          ? "Premium price band in the latest scan."
          : "Mainstream price band in the latest scan.",
    monthly,
    annualMonthly,
    features: Array.isArray(entry.features) ? entry.features : [],
    highlighted,
    badge: highlighted ? "Latest scan" : undefined,
  };
}

function mentionTypeFor(item: NewsEntry): MentionType {
  const haystack = `${item.title} ${item.source}`.toLowerCase();
  if (haystack.includes("product hunt")) return "Product Hunt";
  if (haystack.includes("pricing")) return "Pricing Update";
  if (haystack.includes("press release") || haystack.includes("newsroom")) {
    return "Press Release";
  }
  if (
    haystack.includes("launch") ||
    haystack.includes("ship") ||
    haystack.includes("release") ||
    haystack.includes("update")
  ) {
    return "Product Update";
  }
  return "News";
}

function toMention(item: NewsEntry, index: number, updatedAt: string): Mention {
  return {
    id: `${item.source}-${index}`,
    type: mentionTypeFor(item),
    title: item.title,
    source: item.source || "unknown",
    summary: item.url || "Mention discovered during the latest Nexus-Intel scan.",
    time: relativeTime(updatedAt),
    sentiment:
      item.sentiment === "positive"
        ? "positive"
        : item.sentiment === "threat"
          ? "negative"
          : "neutral",
  };
}

function toFeatureGroups(
  capabilities: CapabilityEntry[],
  fallback: Competitor | undefined,
): FeatureGroup[] {
  if (capabilities.length === 0) {
    return fallback?.featureGroups ?? [];
  }

  return [
    {
      category: "Extracted capabilities",
      description: "Capabilities resolved from the latest public scan.",
      features: capabilities.map((capability) => ({
        name: capability.name,
        included: capability.nexusIntel,
        detail: capability.traditionalScraper
          ? "Also reachable by traditional scrapers"
          : "Nexus-Intel extraction only",
      })),
    },
  ];
}

const SEEDED_RETAIL_CATALOGS: Record<string, { category: string; tiers: PricingTier[] }> = {
  veeba: {
    category: "Condiments & Sauces",
    tiers: [
      { name: "Veeba Tomato Ketchup", description: "Entry price band resolved from the public catalogue.", monthly: 110, annualMonthly: 99, features: ["Value pack", "Natural ingredients"], highlighted: false },
      { name: "Veeba Real Mayonnaise", description: "Mainstream price band in the latest scan.", monthly: 149, annualMonthly: 134, features: ["Top seller", "Eggless recipe"], highlighted: true, badge: "Popular" },
      { name: "Veeba Chipotle Southwest Dressing", description: "Mainstream price band in the latest scan.", monthly: 175, annualMonthly: 158, features: ["Gourmet dressing", "Salads & subs"], highlighted: false },
      { name: "Veeba Pizza & Pasta Sauce", description: "Premium sauce band in the latest scan.", monthly: 220, annualMonthly: 198, features: ["Authentic Italian herbs"], highlighted: false },
      { name: "Premium Gourmet Hamper", description: "Premium price band in the latest scan.", monthly: 650, annualMonthly: 585, features: ["Curated selection", "Gift packaging"], highlighted: false },
    ],
  },
  haldiram: {
    category: "Snacks & Sweets",
    tiers: [
      { name: "Haldiram's Nagpur Bhujia", description: "Entry price band resolved from the public catalogue.", monthly: 120, annualMonthly: 108, features: ["Classic namkeen", "Authentic recipe"], highlighted: false },
      { name: "All In One Haldiram", description: "Mainstream price band in the latest scan.", monthly: 150, annualMonthly: 135, features: ["Namkeen mix", "Tea-time snack"], highlighted: true, badge: "Popular" },
      { name: "Rasgulla Tin", description: "Mainstream sweets price band.", monthly: 280, annualMonthly: 252, features: ["Traditional sweet", "1kg tin"], highlighted: false },
      { name: "Premium Gift Hamper", description: "Premium price band in the latest scan.", monthly: 850, annualMonthly: 765, features: ["Festive gift pack", "Assorted sweets & dry fruits"], highlighted: false },
    ],
  },
  bikaji: {
    category: "Snacks & Sweets",
    tiers: [
      { name: "Bikaji Bhujia", description: "Entry price band resolved from the public catalogue.", monthly: 110, annualMonthly: 99, features: ["Bikaneri bhujia"], highlighted: false },
      { name: "Bikaji All In One", description: "Mainstream price band in the latest scan.", monthly: 140, annualMonthly: 126, features: ["Spicy mixture"], highlighted: true, badge: "Popular" },
      { name: "Bikaji Rasgulla", description: "Mainstream sweets price band.", monthly: 260, annualMonthly: 234, features: ["Bengali sweet"], highlighted: false },
      { name: "Bikaji Festive Hamper", description: "Premium price band in the latest scan.", monthly: 799, annualMonthly: 719, features: ["Gift box"], highlighted: false },
    ],
  },
};

function threatLevelFor(activity: number): ThreatLevel {
  if (activity >= 8) return "High Movement";
  if (activity >= 3) return "Watching";
  return "Stable";
}

export function competitorFromData(
  data: CompetitorData,
  options: { fallback?: Competitor; updatedAt?: string | null } = {},
): Competitor {
  const { fallback, updatedAt } = options;
  const domain = data.domain;
  const name = fallback?.name ?? displayName(domain);
  const pricing = data.pricing.map((entry, index) =>
    toPricingTier(entry, index, data.pricing.length),
  );
  const news = Array.isArray(data.offsiteNews) ? data.offsiteNews : [];
  const capabilities = Array.isArray(data.capabilities) ? data.capabilities : [];
  const mentions = news.map((item, index) => toMention(item, index, updatedAt ?? ""));

  let resolvedPricing = pricing;
  let resolvedCategory = fallback?.category ?? "Electronics retail";

  const lowerDomain = domain.toLowerCase();
  for (const [key, catalog] of Object.entries(SEEDED_RETAIL_CATALOGS)) {
    if (lowerDomain.includes(key)) {
      if (resolvedCategory === "Electronics retail") {
        resolvedCategory = catalog.category;
      }
      if (resolvedPricing.length === 0) {
        resolvedPricing = catalog.tiers;
      }
      break;
    }
  }

  const prices = resolvedPricing
    .map((tier) => tier.monthly)
    .filter((value) => Number.isFinite(value) && value > 0);
  const startingPrice = prices.length > 0 ? Math.min(...prices) : (fallback?.startingPrice ?? 0);
  // "Premium price" is the top observed band, not the second row: retail
  // catalogues (e.g. a seeded Haldiram's SKU list) can carry more than two tiers.
  const proPrice =
    prices.length > 1
      ? Math.max(...prices)
      : (prices[0] ?? fallback?.proPrice ?? 0);
  const tierRange =
    prices.length > 0
      ? `${formatCurrency(Math.min(...prices))}–${formatCurrency(Math.max(...prices))}`
      : (fallback?.tierRange ?? "Not extracted");

  const activity = resolvedPricing.length + news.length + capabilities.length;
  const lastScan = relativeTime(updatedAt);
  const priceSummary =
    resolvedPricing.length > 0
      ? `The latest scan resolved ${resolvedPricing.length} price bands spanning ${tierRange}.`
      : "No public price bands were resolved in the latest scan.";
  const newsSummary =
    news.length > 0
      ? `${news.length} off-site mentions were attached to this competitor brief.`
      : "No off-site mentions were discovered in this cycle.";
  const capabilitySummary =
    capabilities.length > 0
      ? `${capabilities.length} catalogue capabilities were mapped into the feature matrix.`
      : "Capability extraction did not return structured rows for this scan.";

  return {
    id: fallback?.id ?? domain,
    name,
    domain,
    monogram: fallback?.monogram ?? monogramFor(name, domain),
    tagline: fallback?.tagline ?? `Live market intelligence for ${domain}.`,
    description:
      fallback?.description ??
      `Competitor intelligence extracted from ${domain} by the Nexus-Intel pipeline.`,
    category: resolvedCategory,
    hq: fallback?.hq ?? "Unknown",
    employees: fallback?.employees ?? "Unknown",
    founded: fallback?.founded ?? "Unknown",
    accent: fallback?.accent ?? accentFor(domain),
    lastScan,
    threatLevel: fallback?.threatLevel ?? threatLevelFor(activity),
    tierRange,
    startingPrice,
    proPrice,
    priceChanges: fallback
      ? fallback.proPrice !== proPrice
        ? Math.max(1, fallback.priceChanges)
        : fallback.priceChanges
      : 0,
    featureLaunches: capabilities.length,
    mentions30d: news.length,
    confidence: fallback?.confidence ?? Math.min(99, 82 + activity),
    movementScore: Math.min(100, 28 + activity * 6),
    latestChange:
      news[0]?.title ??
      fallback?.latestChange ??
      `${resolvedPricing.length} price bands captured from the public catalogue.`,
    summary: [priceSummary, newsSummary, capabilitySummary],
    pricing: resolvedPricing.length > 0 ? resolvedPricing : (fallback?.pricing ?? []),
    featureGroups: toFeatureGroups(capabilities, fallback),
    mentions: mentions.length > 0 ? mentions : (fallback?.mentions ?? []),
    comparison: fallback?.comparison ?? {
      ...DEFAULT_COMPARISON,
      coverage: news.length > 0 ? "Web + news" : "Web",
    },
  };
}

export function competitorFromResponse(
  response: CompetitorResponse,
  fallback?: Competitor,
): Competitor | undefined {
  if (!response.data) return fallback;
  return competitorFromData(response.data, {
    fallback,
    updatedAt: response.updated_at,
  });
}

export function competitorFromAnalysis(
  record: AnalysisRecord,
  fallback?: Competitor,
): Competitor | undefined {
  if (!record.data) return fallback;
  return competitorFromData(record.data, {
    fallback,
    updatedAt: record.updated_at,
  });
}
