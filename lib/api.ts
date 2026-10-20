import { getMockCompetitorData, normalizeDomain, type CompetitorData } from "./mockData";

/**
 * Flip this single flag to route the dashboard to the FastAPI backend.
 * The UI, stepper, and schema stay identical in both modes.
 */
export const USE_MOCK_DATA = true;

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const ANALYSIS_ENDPOINT = `${API_BASE_URL}/api/v1/analyze`;

export type StepStatus = "pending" | "active" | "complete" | "error";

export type StepProgressHandler = (index: number, status: StepStatus) => void;

export interface AnalysisOptions {
  pricingTiers: boolean;
  featureAccordions: boolean;
  offsiteMentions: boolean;
}

export const DEFAULT_ANALYSIS_OPTIONS: AnalysisOptions = {
  pricingTiers: true,
  featureAccordions: true,
  offsiteMentions: true,
};

const DOMAIN_PATTERN = /^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$/;

const MOCK_STEP_DURATIONS_MS = [700, 700, 650, 550, 400];
const LIVE_STEP_DURATIONS_MS = [900, 1150, 950, 800, 600];

const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

function assertDomain(domain: string): string {
  const normalized = normalizeDomain(domain);
  if (!normalized || !DOMAIN_PATTERN.test(normalized)) {
    throw new Error("Enter a valid competitor domain, for example stripe.com.");
  }
  return normalized;
}

function isCompetitorData(value: unknown): value is CompetitorData {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<CompetitorData>;
  return (
    typeof candidate.domain === "string" &&
    Array.isArray(candidate.pricing) &&
    Array.isArray(candidate.offsiteNews) &&
    Array.isArray(candidate.capabilities) &&
    typeof candidate.executionTimeSec === "number"
  );
}

async function runMockAnalysis(
  domain: string,
  onProgress?: StepProgressHandler,
): Promise<CompetitorData> {
  for (let index = 0; index < MOCK_STEP_DURATIONS_MS.length; index += 1) {
    onProgress?.(index, "active");
    await wait(MOCK_STEP_DURATIONS_MS[index]);
    onProgress?.(index, "complete");
  }

  return getMockCompetitorData(domain);
}

async function runLiveAnalysis(
  domain: string,
  options: AnalysisOptions,
  onProgress?: StepProgressHandler,
): Promise<CompetitorData> {
  let cancelled = false;
  let activeStep = 0;

  const simulatePipeline = (async () => {
    for (let index = 0; index < LIVE_STEP_DURATIONS_MS.length; index += 1) {
      if (cancelled) return;
      activeStep = index;
      onProgress?.(index, "active");
      await wait(LIVE_STEP_DURATIONS_MS[index]);
      if (cancelled) return;
      onProgress?.(index, "complete");
    }
  })();

  try {
    const response = await fetch(ANALYSIS_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        domain,
        parameters: {
          pricing_tiers: options.pricingTiers,
          feature_accordions: options.featureAccordions,
          offsite_mentions: options.offsiteMentions,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(
        `The intelligence engine responded with ${response.status} ${response.statusText}.`,
      );
    }

    const raw = await response.json();
    const payload = raw?.data ?? raw?.result ?? raw;

    if (!isCompetitorData(payload)) {
      throw new Error("The intelligence engine returned an unexpected payload shape.");
    }

    cancelled = true;
    for (let index = 0; index < LIVE_STEP_DURATIONS_MS.length; index += 1) {
      onProgress?.(index, "complete");
    }

    return payload;
  } catch (error) {
    cancelled = true;
    onProgress?.(activeStep, "error");

    if (error instanceof TypeError) {
      throw new Error(
        `Cannot reach the intelligence API at ${ANALYSIS_ENDPOINT}. Is the FastAPI service running?`,
      );
    }

    throw error instanceof Error
      ? error
      : new Error("The autonomous analysis run failed unexpectedly.");
  } finally {
    void simulatePipeline;
  }
}

/**
 * Runs the autonomous competitor analysis.
 *
 * Mock mode resolves in ~3 seconds, emitting live step transitions so the
 * execution stepper behaves exactly like the production pipeline.
 */
export async function analyzeCompetitor(
  domain: string,
  options: AnalysisOptions = DEFAULT_ANALYSIS_OPTIONS,
  onProgress?: StepProgressHandler,
): Promise<CompetitorData> {
  const normalized = assertDomain(domain);

  if (USE_MOCK_DATA) {
    return runMockAnalysis(normalized, onProgress);
  }

  return runLiveAnalysis(normalized, options, onProgress);
}
