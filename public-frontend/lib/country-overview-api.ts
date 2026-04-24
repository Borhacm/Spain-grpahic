import {
  getCountryOverviewSeedData,
  type CountryOverviewData,
  type CountrySection,
  type KpiMetric
} from "@/lib/country-overview";

type LiveOverviewPayload = Partial<{
  executiveKpis: Array<Partial<KpiMetric> & { id: string }>;
  executiveNarrative: string[];
  sections: Array<
    Partial<CountrySection> & {
      id: string;
      indicators?: Array<{ id: string } & Record<string, unknown>>;
    }
  >;
}>;

type SourceName = "BdE" | "INE" | "Eurostat" | "OECD" | "FMI";

const SOURCE_ENDPOINTS: Array<{ source: SourceName; envKey: string }> = [
  { source: "BdE", envKey: "COUNTRY_OVERVIEW_BDE_URL" },
  { source: "INE", envKey: "COUNTRY_OVERVIEW_INE_URL" },
  { source: "Eurostat", envKey: "COUNTRY_OVERVIEW_EUROSTAT_URL" },
  { source: "OECD", envKey: "COUNTRY_OVERVIEW_OECD_URL" },
  { source: "FMI", envKey: "COUNTRY_OVERVIEW_FMI_URL" }
];

const API_BASE_URL = process.env.NEXT_PUBLIC_STORIES_API_BASE_URL ?? "http://localhost:8000";

function mergeKpis(base: KpiMetric[], incoming: Array<Partial<KpiMetric> & { id: string }>): KpiMetric[] {
  const byId = new Map(incoming.map((item) => [item.id, item]));
  return base.map((kpi) => {
    const patch = byId.get(kpi.id);
    if (!patch) return kpi;
    return {
      ...kpi,
      ...patch,
      trend: Array.isArray(patch.trend) && patch.trend.length > 1 ? patch.trend : kpi.trend
    };
  });
}

function mergeSections(
  base: CountrySection[],
  incoming: LiveOverviewPayload["sections"] | undefined
): CountrySection[] {
  if (!incoming?.length) return base;
  const sectionById = new Map(incoming.map((section) => [section.id, section]));

  return base.map((section) => {
    const sectionPatch = sectionById.get(section.id);
    if (!sectionPatch) return section;

    const indicatorPatches = new Map((sectionPatch.indicators ?? []).map((item) => [item.id, item]));
    return {
      ...section,
      ...sectionPatch,
      indicators: section.indicators.map((indicator) => {
        const patch = indicatorPatches.get(indicator.id);
        if (!patch) return indicator;
        return {
          ...indicator,
          ...patch,
          series: Array.isArray(patch.series) ? patch.series : indicator.series
        };
      })
    };
  });
}

async function fetchLivePayload(url: string): Promise<LiveOverviewPayload | null> {
  try {
    const response = await fetch(url, { next: { revalidate: 3600 } });
    if (!response.ok) return null;
    const data = (await response.json()) as unknown;
    if (!data || typeof data !== "object") return null;
    const raw = data as Record<string, unknown>;
    const executiveKpis = Array.isArray(raw.executive_kpis)
      ? (raw.executive_kpis as Array<Record<string, unknown>>).map((kpi) => ({
          ...kpi,
          updatedAt: (kpi.updatedAt as string | undefined) ?? (kpi.updated_at as string | undefined)
        }))
      : raw.executiveKpis;

    return {
      executiveKpis: Array.isArray(executiveKpis) ? (executiveKpis as LiveOverviewPayload["executiveKpis"]) : undefined,
      executiveNarrative: (raw.executive_narrative as string[] | undefined) ?? (raw.executiveNarrative as string[] | undefined),
      sections: raw.sections as LiveOverviewPayload["sections"]
    };
  } catch {
    return null;
  }
}

function normalizedBaseUrl(): string {
  return API_BASE_URL.endsWith("/") ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
}

function mergePayload(base: CountryOverviewData, payload: LiveOverviewPayload): CountryOverviewData {
  return {
    executiveKpis: payload.executiveKpis?.length
      ? mergeKpis(base.executiveKpis, payload.executiveKpis)
      : base.executiveKpis,
    executiveNarrative: payload.executiveNarrative?.length ? payload.executiveNarrative : base.executiveNarrative,
    sections: mergeSections(base.sections, payload.sections)
  };
}

/**
 * Carga datos "live" por fuente cuando existen endpoints configurados.
 * Si una fuente falla, mantiene los seeds para evitar degradación funcional.
 */
export async function getCountryOverviewData(): Promise<CountryOverviewData> {
  const seedData = getCountryOverviewSeedData();
  let data = seedData;

  const unifiedUrl = process.env.COUNTRY_OVERVIEW_API_URL ?? `${normalizedBaseUrl()}/public/country-overview`;
  const unifiedPayload = await fetchLivePayload(unifiedUrl);
  if (unifiedPayload) {
    data = mergePayload(seedData, unifiedPayload);
    return data;
  }

  for (const endpoint of SOURCE_ENDPOINTS) {
    const url = process.env[endpoint.envKey];
    if (!url) continue;
    const payload = await fetchLivePayload(url);
    if (!payload) continue;
    data = mergePayload(data, payload);
  }

  return data;
}
