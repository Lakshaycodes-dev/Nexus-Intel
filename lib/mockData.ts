export type Sentiment = "positive" | "threat" | "neutral";

export interface CompetitorData {
  domain: string;
  pricing: { tier: string; monthly: string; annual: string; features: string[] }[];
  offsiteNews: { title: string; source: string; url: string; sentiment: Sentiment }[];
  capabilities: { name: string; traditionalScraper: boolean; nexusIntel: boolean }[];
  executionTimeSec: number;
}

const CAPABILITIES: CompetitorData["capabilities"] = [
  { name: "Static Page", traditionalScraper: true, nexusIntel: true },
  { name: "JS-rendered DOM", traditionalScraper: false, nexusIntel: true },
  { name: "Hidden Accordions", traditionalScraper: false, nexusIntel: true },
  { name: "Off-site Mentions", traditionalScraper: false, nexusIntel: true },
];

const MOCK_COMPETITORS: Record<string, CompetitorData> = {
  "stripe.com": {
    domain: "stripe.com",
    pricing: [
      {
        tier: "Starter",
        monthly: "$0",
        annual: "$0",
        features: [
          "Standard checkout",
          "Basic dashboard",
          "2-day rolling payouts",
        ],
      },
      {
        tier: "Growth",
        monthly: "$99",
        annual: "$79",
        features: [
          "Advanced fraud protection",
          "Recurring billing engine",
          "Priority support",
          "Custom invoicing",
        ],
      },
      {
        tier: "Scale",
        monthly: "$299",
        annual: "$239",
        features: [
          "Volume discount routing",
          "Dedicated success manager",
          "Custom contracts & SLAs",
          "Multi-entity reporting",
        ],
      },
    ],
    offsiteNews: [
      {
        title: "Stripe expands stablecoin payouts across 12 new markets",
        source: "TechCrunch",
        url: "https://techcrunch.com/category/fintech/",
        sentiment: "threat",
      },
      {
        title: "Stripe named a Leader in payment orchestration platforms",
        source: "Gartner",
        url: "https://www.gartner.com/en/newsroom",
        sentiment: "positive",
      },
      {
        title: "Developers weigh switching costs after Stripe's new fee update",
        source: "Hacker News",
        url: "https://news.ycombinator.com/",
        sentiment: "neutral",
      },
      {
        title: "EU regulators open review of Stripe's acquiring practices",
        source: "Reuters",
        url: "https://www.reuters.com/technology/",
        sentiment: "threat",
      },
    ],
    capabilities: CAPABILITIES,
    executionTimeSec: 30.4,
  },
  "acme.com": {
    domain: "acme.com",
    pricing: [
      {
        tier: "Base",
        monthly: "$49",
        annual: "$39",
        features: [
          "5 workspace seats",
          "Standard automations",
          "Email support",
        ],
      },
      {
        tier: "Pro",
        monthly: "$149",
        annual: "$119",
        features: [
          "Unlimited workflows",
          "Advanced analytics",
          "SSO & audit logs",
          "Priority support",
        ],
      },
      {
        tier: "Enterprise",
        monthly: "$399",
        annual: "$319",
        features: [
          "Dedicated infrastructure",
          "Custom data residency",
          "99.99% uptime SLA",
          "Named solution architect",
        ],
      },
    ],
    offsiteNews: [
      {
        title: "Acme Cloud announces SOC 2 Type II certification",
        source: "SecurityWeek",
        url: "https://www.securityweek.com/",
        sentiment: "positive",
      },
      {
        title: "Acme's new usage-based pricing draws mixed community reaction",
        source: "Reddit · r/SaaS",
        url: "https://www.reddit.com/r/SaaS/",
        sentiment: "threat",
      },
      {
        title: "Acme recognized as a Visionary in 2026 workflow automation report",
        source: "Gartner",
        url: "https://www.gartner.com/en/newsroom",
        sentiment: "positive",
      },
      {
        title: "Acme acquires workflow automation startup for reported $84M",
        source: "Business Wire",
        url: "https://www.businesswire.com/news/home",
        sentiment: "neutral",
      },
    ],
    capabilities: CAPABILITIES,
    executionTimeSec: 30.1,
  },
};

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

export function normalizeDomain(input: string): string {
  const trimmed = input.trim().toLowerCase();
  if (!trimmed) return "";

  return trimmed
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split(/[/?#]/)[0]
    .replace(/:\d+$/, "");
}

export function getCompanyName(domain: string): string {
  const label = normalizeDomain(domain).split(".")[0] || "Competitor";
  return label
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function getMockCompetitorData(domain: string): CompetitorData {
  const normalized = normalizeDomain(domain) || "stripe.com";
  const known = MOCK_COMPETITORS[normalized];
  if (known) {
    return structuredClone(known);
  }

  const seed = hashString(normalized);
  const company = getCompanyName(normalized);
  const base = 39 + (seed % 6) * 10;
  const pro = base + 100 + (seed % 4) * 10;
  const enterprise = pro + 200 + (seed % 5) * 20;
  const annualDiscount = (value: number) => Math.round(value * 0.8);

  return {
    domain: normalized,
    pricing: [
      {
        tier: "Launch",
        monthly: `$${base}`,
        annual: `$${annualDiscount(base)}`,
        features: [
          `${3 + (seed % 4)} workspace seats`,
          "Core analytics",
          "Community support",
        ],
      },
      {
        tier: "Growth",
        monthly: `$${pro}`,
        annual: `$${annualDiscount(pro)}`,
        features: [
          "Unlimited automations",
          "Advanced reporting",
          "SSO & audit logs",
          "Priority support",
        ],
      },
      {
        tier: "Enterprise",
        monthly: `$${enterprise}`,
        annual: `$${annualDiscount(enterprise)}`,
        features: [
          "Custom contracts & SLAs",
          "Dedicated success manager",
          "Multi-region deployment",
          "Security review support",
        ],
      },
    ],
    offsiteNews: [
      {
        title: `${company} expands platform capabilities with new enterprise release`,
        source: "TechCrunch",
        url: "https://techcrunch.com/category/startups/",
        sentiment: "neutral",
      },
      {
        title: `${company} pricing changes spark debate among long-term customers`,
        source: "Reddit",
        url: "https://www.reddit.com/r/SaaS/",
        sentiment: "threat",
      },
      {
        title: `${company} reports strong momentum in latest market update`,
        source: "Business Wire",
        url: "https://www.businesswire.com/news/home",
        sentiment: "positive",
      },
    ],
    capabilities: CAPABILITIES,
    executionTimeSec: Number((29.8 + (seed % 12) / 10).toFixed(1)),
  };
}
