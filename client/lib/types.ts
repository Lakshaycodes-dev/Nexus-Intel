export type ScopeKey = "pricing" | "product" | "news";

export type ThreatLevel = "High Movement" | "Watching" | "Stable";

export type MentionType =
  | "News"
  | "Press Release"
  | "Product Hunt"
  | "Pricing Update"
  | "Product Update";

export type Sentiment = "positive" | "neutral" | "negative";

export interface Accent {
  gradient: string;
  solid: string;
  soft: string;
  text: string;
  hex: string;
}

export interface PricingTier {
  name: string;
  description: string;
  monthly: number;
  annualMonthly: number;
  features: string[];
  highlighted?: boolean;
  badge?: string;
}

export interface Feature {
  name: string;
  included: boolean;
  detail?: string;
}

export interface FeatureGroup {
  category: string;
  description: string;
  features: Feature[];
}

export interface Mention {
  id: string;
  type: MentionType;
  title: string;
  source: string;
  summary: string;
  time: string;
  sentiment: Sentiment;
}

export interface ComparisonProfile {
  refreshMinutes: number;
  coverage: string;
  retentionMonths: number;
  freeTrialDays: number;
  sso: boolean;
  soc2: boolean;
  auditLogs: boolean;
  slack: boolean;
  api: boolean;
  webhooks: boolean;
  crm: string;
  p1Response: string;
  dedicatedCsm: boolean;
  onboarding: string;
}

export interface Competitor {
  id: string;
  name: string;
  domain: string;
  monogram: string;
  tagline: string;
  description: string;
  category: string;
  hq: string;
  employees: string;
  founded: string;
  accent: Accent;
  lastScan: string;
  threatLevel: ThreatLevel;
  tierRange: string;
  startingPrice: number;
  proPrice: number;
  priceChanges: number;
  featureLaunches: number;
  mentions30d: number;
  confidence: number;
  movementScore: number;
  latestChange: string;
  summary: string[];
  pricing: PricingTier[];
  featureGroups: FeatureGroup[];
  mentions: Mention[];
  comparison: ComparisonProfile;
}

export interface MarketSignal {
  id: string;
  competitorId: string;
  competitor: string;
  monogram: string;
  accent: Accent;
  type: MentionType;
  title: string;
  source: string;
  time: string;
  impact: "High" | "Medium" | "Low";
  summary: string;
}

export interface MyProduct {
  name: string;
  domain: string;
  startingPrice: number;
  proPrice: number;
  comparison: ComparisonProfile;
}

export type ScanStatus = "pending" | "active" | "complete";

export interface ExecutionStep {
  id: number;
  title: string;
  shortTitle: string;
  description: string;
  startAt: number;
  endAt: number;
}

export interface TerminalLine {
  time: string;
  at: number;
  level: "info" | "success" | "muted";
  message: string;
}
