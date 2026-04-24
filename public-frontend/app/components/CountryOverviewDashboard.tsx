"use client";

import { useEffect, useMemo, useState } from "react";

import {
  type CountryOverviewData,
  type DataSource,
  type DataStatus,
  type KpiMetric,
  getCountryOverviewSeedData
} from "@/lib/country-overview";

function sourceClassName(source: DataSource): string {
  return `source-badge source-badge--${source.toLowerCase()}`;
}

function statusClassName(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized.includes("desactual")) return "status-badge status-badge--stale";
  if (normalized.includes("provisional")) return "status-badge status-badge--provisional";
  if (normalized.includes("revisado")) return "status-badge status-badge--revised";
  return "status-badge status-badge--latest";
}

function Sparkline({ points }: { points: number[] }) {
  const width = 96;
  const height = 28;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;

  const coordinates = points
    .map((value, index) => {
      const x = (index / (points.length - 1 || 1)) * width;
      const normalized = (value - min) / range;
      const y = height - normalized * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} aria-hidden="true" focusable="false">
      <polyline points={coordinates} />
    </svg>
  );
}

type HistoryPoint = {
  period: string;
  value: number;
};

type HorizonPreset = "1A" | "5A" | "15A" | "30A";

type DetailState = {
  id: string;
  title: string;
  source: DataSource;
  status: DataStatus;
  value: string;
  delta: string;
  updatedAt: string;
  history: HistoryPoint[];
  unit: string;
  note?: string;
};

type MetricVariant = {
  conceptKey: string;
  source: DataSource;
  status: DataStatus;
  value: string;
  delta: string;
  updatedAt: string;
  history: HistoryPoint[];
  unit: string;
  note?: string;
};

type OecdRanking = {
  indicator_id: string;
  country_code: string;
  value: number;
  scale: string;
  rank: number;
  total_countries: number;
  year: string | null;
};

const SECTION_ICONS: Record<string, string> = {
  resumen: "🇪🇸",
  laboral: "💼",
  "digitalizacion-empleo": "💻",
  "demografia-vivienda": "🏘️",
  "empresa-actividad": "🏭",
  "proyecciones-fmi": "🌍"
};

type RenderedKpiItem = {
  conceptKey: string;
  kpi: KpiMetric;
  history: HistoryPoint[];
  unit: string;
  note?: string;
  options: DataSource[];
};

const CONCEPT_ALLOWED_SOURCES: Partial<Record<string, DataSource[]>> = {
  paro: ["INE", "FMI"],
  "deuda-publica": ["BdE", "FMI"],
  "saldo-publico": ["Eurostat", "FMI"],
  pib: ["BdE", "FMI"],
  inflacion: ["INE", "FMI"],
  poblacion: ["INE"],
  ocupacion: ["INE"],
  vacantes: ["Eurostat"]
};

function normalizeForUnitHints(text: string): string {
  return text.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
}

/**
 * Unit for the modal must follow the **headline value** on the card.
 * Deltas often contain "%" (e.g. "+1,8% interanual") even when the level is in mil / M / EUR;
 * mixing delta into the same string as the value used to force "%" incorrectly.
 */
function inferUnitFromPrimaryDisplay(primary: string): string | null {
  const v = normalizeForUnitHints(primary);
  if (!v.trim()) return null;

  if (v.includes("/10")) return "/10";
  if (v.includes("eur/mes") || v.includes("eur / mes")) return "EUR/mes";
  if (v.includes("mil") && v.includes("eur")) return "mil EUR";
  if (v.includes("eur")) return "EUR";
  if (v.includes(" mil")) return "mil";
  if (/\bm\b/.test(v)) return "M";
  if (v.includes("%")) return "%";
  return null;
}

function inferUnit(value: string, delta: string, label: string): string {
  const vNorm = normalizeForUnitHints(value).replace(/\s/g, "");
  if (vNorm === "n/d" || vNorm === "nd") return "índice";

  const fromValue = inferUnitFromPrimaryDisplay(value);
  if (fromValue !== null) return fromValue;

  const fromLabel = inferUnitFromPrimaryDisplay(label);
  if (fromLabel !== null) return fromLabel;

  const d = normalizeForUnitHints(delta);
  if (d.includes("pp")) return "%";

  return "índice";
}

function isOecdDigitalIndex(detail: DetailState | null): boolean {
  if (!detail) return false;
  return detail.id === "digital-oecd-dgi" || detail.id === "digital-oecd-ourdata";
}

function oecdRankingHint(detail: DetailState | null): string | null {
  if (!isOecdDigitalIndex(detail)) return null;
  return null;
}

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

function inferHistoryPeriods(updatedAt: string, length: number): string[] {
  const trimmed = updatedAt.trim();
  const qMatch = /^Q([1-4])\s+(\d{4})$/i.exec(trimmed);
  if (qMatch) {
    let quarter = Number(qMatch[1]);
    let year = Number(qMatch[2]);
    const periods: string[] = [];
    for (let idx = 0; idx < length; idx += 1) {
      periods.unshift(`Q${quarter} ${year}`);
      quarter -= 1;
      if (quarter === 0) {
        quarter = 4;
        year -= 1;
      }
    }
    return periods;
  }

  const monthMap: Record<string, number> = {
    ene: 1,
    feb: 2,
    mar: 3,
    abr: 4,
    may: 5,
    jun: 6,
    jul: 7,
    ago: 8,
    sep: 9,
    oct: 10,
    nov: 11,
    dic: 12
  };
  const mMatch = /^([a-záéíóú]{3})\s+(\d{4})$/i.exec(trimmed);
  if (mMatch) {
    const key = mMatch[1].toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
    if (monthMap[key]) {
      let month = monthMap[key];
      let year = Number(mMatch[2]);
      const periods: string[] = [];
      for (let idx = 0; idx < length; idx += 1) {
        periods.unshift(`${year}-${pad2(month)}`);
        month -= 1;
        if (month === 0) {
          month = 12;
          year -= 1;
        }
      }
      return periods;
    }
  }

  const yMatch = /^(\d{4})$/.exec(trimmed);
  if (yMatch) {
    const latestYear = Number(yMatch[1]);
    return Array.from({ length }, (_, idx) => String(latestYear - (length - idx - 1)));
  }

  const ymMatch = /^(\d{4})-(\d{2})$/.exec(trimmed);
  if (ymMatch) {
    let year = Number(ymMatch[1]);
    let month = Number(ymMatch[2]);
    const periods: string[] = [];
    for (let idx = 0; idx < length; idx += 1) {
      periods.unshift(`${year}-${pad2(month)}`);
      month -= 1;
      if (month === 0) {
        month = 12;
        year -= 1;
      }
    }
    return periods;
  }

  const ymdMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
  if (ymdMatch) {
    let year = Number(ymdMatch[1]);
    let month = Number(ymdMatch[2]);
    const periods: string[] = [];
    for (let idx = 0; idx < length; idx += 1) {
      periods.unshift(`${year}-${pad2(month)}`);
      month -= 1;
      if (month === 0) {
        month = 12;
        year -= 1;
      }
    }
    return periods;
  }

  return Array.from({ length }, (_, idx) => `Obs ${idx + 1}`);
}

function formatHistoryNumber(value: number, unit: string, contextTitle: string = ""): string {
  const normalizedTitle = contextTitle.toLowerCase();
  const isPopulation = normalizedTitle.includes("poblaci");
  if (unit === "/10") {
    const core10 = value.toFixed(1).replace(".", ",");
    return `${core10}/10`;
  }
  // Card shows "49,6 M" / "22,5 M" but feeds may store personas (1e6) or INE miles de personas (1e3).
  let v = value;
  if (unit === "M") {
    const av = Math.abs(value);
    if (av >= 1_000_000) v = value / 1_000_000;
    else if (av >= 5_000) v = value / 1_000;
  }
  const isOcupacionMillions = normalizedTitle.includes("ocupaci");
  const decimals =
    isPopulation && unit === "M"
      ? 1
      : isOcupacionMillions && unit === "M"
        ? 1
        : isPopulation
          ? 0
          : Number.isInteger(v)
            ? 0
            : 2;
  const core =
    decimals === 0 ? String(Math.round(v)) : v.toFixed(decimals).replace(".", ",");
  if (unit === "%" || unit === "EUR") return `${core} ${unit}`;
  if (unit === "EUR/mes") return `${core.replace(".", ",")} EUR/mes`;
  if (unit === "mil EUR") return `${core.replace(".", ",")} mil EUR`;
  if (unit === "M" || unit === "mil") return `${core} ${unit}`;
  return core;
}

function parseHistoryDate(period: string): Date | null {
  const trimmed = period.trim();
  const ymd = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
  if (ymd) return new Date(Date.UTC(Number(ymd[1]), Number(ymd[2]) - 1, Number(ymd[3])));
  const ym = /^(\d{4})-(\d{2})$/.exec(trimmed);
  if (ym) return new Date(Date.UTC(Number(ym[1]), Number(ym[2]) - 1, 1));
  const q = /^Q([1-4])\s+(\d{4})$/i.exec(trimmed);
  if (q) return new Date(Date.UTC(Number(q[2]), (Number(q[1]) - 1) * 3, 1));
  const y = /^(\d{4})$/.exec(trimmed);
  if (y) return new Date(Date.UTC(Number(y[1]), 0, 1));
  return null;
}

function latestByBucket(points: HistoryPoint[], bucketKey: (date: Date) => string): HistoryPoint[] {
  const byBucket = new Map<string, HistoryPoint>();
  for (const point of points) {
    const date = parseHistoryDate(point.period);
    if (!date) continue;
    byBucket.set(bucketKey(date), point);
  }
  return Array.from(byBucket.values()).sort((a, b) => {
    const da = parseHistoryDate(a.period)?.getTime() ?? 0;
    const db = parseHistoryDate(b.period)?.getTime() ?? 0;
    return da - db;
  });
}

function downsampleEvenly(points: HistoryPoint[], targetCount: number): HistoryPoint[] {
  if (points.length <= targetCount) return points;
  const step = (points.length - 1) / (targetCount - 1);
  const selected: HistoryPoint[] = [];
  for (let idx = 0; idx < targetCount; idx += 1) {
    const point = points[Math.round(idx * step)];
    if (point) selected.push(point);
  }
  const deduped = selected.filter((point, index, arr) => index === 0 || point.period !== arr[index - 1]?.period);
  return deduped.length >= 2 ? deduped : [points[0], points[points.length - 1]];
}

function compactSeriesForCard(series: HistoryPoint[], targetCount: number = 5): HistoryPoint[] {
  if (series.length <= targetCount) return series;
  return downsampleEvenly(series, targetCount);
}

function compactTrendForCard(trend: number[], targetCount: number = 28): number[] {
  if (trend.length <= targetCount) return trend;
  const points = trend.map((value, index) => ({ period: String(index), value }));
  return downsampleEvenly(points, targetCount).map((point) => point.value);
}

function getDatedHistory(history: HistoryPoint[]): { point: HistoryPoint; date: Date }[] {
  return history
    .map((point) => ({ point, date: parseHistoryDate(point.period) }))
    .filter((item): item is { point: HistoryPoint; date: Date } => Boolean(item.date))
    .sort((a, b) => a.date.getTime() - b.date.getTime());
}

function getWindowedPoints(
  dated: { point: HistoryPoint; date: Date }[],
  horizon: HorizonPreset
): { point: HistoryPoint; date: Date }[] {
  if (!dated.length) return [];
  const latest = dated[dated.length - 1].date;
  const yearsWindow = horizon === "1A" ? 1 : horizon === "5A" ? 5 : horizon === "15A" ? 15 : 30;
  const start = new Date(Date.UTC(latest.getUTCFullYear() - yearsWindow, latest.getUTCMonth(), latest.getUTCDate()));
  return dated.filter((item) => item.date >= start);
}

function horizonYears(horizon: HorizonPreset): number {
  return horizon === "1A" ? 1 : horizon === "5A" ? 5 : horizon === "15A" ? 15 : 30;
}

function hasRealCoverageForHorizon(dated: { point: HistoryPoint; date: Date }[], horizon: HorizonPreset): boolean {
  if (dated.length < 2) return false;
  const first = dated[0].date;
  const last = dated[dated.length - 1].date;
  const spanYears = (last.getTime() - first.getTime()) / (1000 * 60 * 60 * 24 * 365.25);
  const requiredYears = horizonYears(horizon);
  if (spanYears < requiredYears - 0.25) return false;
  const pointsInWindow = getWindowedPoints(dated, horizon).length;
  const minPointsByHorizon: Record<HorizonPreset, number> = { "1A": 2, "5A": 4, "15A": 6, "30A": 8 };
  return pointsInWindow >= minPointsByHorizon[horizon];
}

function sampleByHorizon(points: HistoryPoint[], horizon: HorizonPreset): HistoryPoint[] {
  let sampled: HistoryPoint[];
  if (horizon === "1A") {
    sampled = latestByBucket(points, (date) => `${date.getUTCFullYear()}-Q${Math.floor(date.getUTCMonth() / 3) + 1}`);
  } else if (horizon === "5A") {
    sampled = latestByBucket(points, (date) => `${date.getUTCFullYear()}`);
  } else if (horizon === "15A") {
    sampled = latestByBucket(points, (date) => `${Math.floor(date.getUTCFullYear() / 3) * 3}`);
  } else {
    sampled = latestByBucket(points, (date) => `${Math.floor(date.getUTCFullYear() / 5) * 5}`);
  }

  // Preserve full coverage in the selected window so wider horizons don't "start later".
  const first = points[0];
  const last = points[points.length - 1];
  const merged = [first, ...sampled, last];
  return merged.filter((point, index, arr) => index === 0 || point.period !== arr[index - 1]?.period);
}

function filterHistoryByHorizon(history: HistoryPoint[], horizon: HorizonPreset, allowFallback: boolean = true): HistoryPoint[] {
  if (history.length <= 2) return history;
  const dated = getDatedHistory(history);
  if (dated.length < 2) return history;

  const windowed = getWindowedPoints(dated, horizon).map((item) => item.point);
  if (windowed.length < 2) {
    if (!allowFallback) return [];
    return downsampleEvenly(dated.map((item) => item.point), horizon === "30A" ? 7 : 6);
  }

  const sampled = sampleByHorizon(windowed, horizon);
  if (sampled.length >= 2) return sampled;
  if (!allowFallback) return [];

  const base = dated.map((item) => item.point);
  const fallbackTargets: Record<HorizonPreset, number> = { "1A": 6, "5A": 6, "15A": 6, "30A": 7 };
  return downsampleEvenly(base, fallbackTargets[horizon]);
}

function recommendDefaultHorizon(history: HistoryPoint[]): HorizonPreset {
  if (history.length < 2) return "1A";
  const dated = history
    .map((point) => parseHistoryDate(point.period))
    .filter((value): value is Date => Boolean(value))
    .sort((a, b) => a.getTime() - b.getTime());
  if (dated.length < 2) return "5A";
  const yearsSpan = (dated[dated.length - 1].getTime() - dated[0].getTime()) / (1000 * 60 * 60 * 24 * 365.25);
  if (yearsSpan <= 2) return "1A";
  if (yearsSpan <= 8) return "5A";
  if (yearsSpan <= 20) return "15A";
  return "30A";
}

function buildKpiHistory(kpi: KpiMetric): HistoryPoint[] {
  const inferredPeriods = inferHistoryPeriods(kpi.updatedAt, kpi.trend.length);
  return kpi.trend.map((value, index) => ({
    period: inferredPeriods[index] ?? `Obs ${index + 1}`,
    value
  }));
}

function DetailChart({ points, unit, title }: { points: HistoryPoint[]; unit: string; title: string }) {
  const width = 560;
  const height = 180;
  const paddingLeft = 18;
  const paddingRight = 50;
  const paddingTop = 12;
  const paddingBottom = 26;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;
  const min = Math.min(...points.map((point) => point.value));
  const max = Math.max(...points.map((point) => point.value));
  const range = max - min || 1;
  const yTicks = [max, min];
  const xStep = points.length <= 8 ? 1 : Math.ceil(points.length / 4);
  const coordinates = points
    .map((point, index) => {
      const x = paddingLeft + (index / (points.length - 1 || 1)) * chartWidth;
      const normalized = (point.value - min) / range;
      const y = paddingTop + (1 - normalized) * chartHeight;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg className="detail-chart" viewBox={`0 0 ${width} ${height}`} aria-hidden="true" focusable="false">
      <line
        className="detail-chart__axis"
        x1={paddingLeft}
        y1={paddingTop + chartHeight}
        x2={paddingLeft + chartWidth}
        y2={paddingTop + chartHeight}
      />
      {yTicks.map((tick) => {
        const normalized = (tick - min) / range;
        const y = paddingTop + (1 - normalized) * chartHeight;
        return (
          <g key={`y-${tick}`}>
            <line className="detail-chart__grid" x1={paddingLeft} y1={y} x2={paddingLeft + chartWidth} y2={y} />
            <text className="detail-chart__tick" x={paddingLeft + chartWidth + 6} y={y + 4}>
              {formatHistoryNumber(tick, unit, title)}
            </text>
          </g>
        );
      })}
      {points.map((point, index) => {
        const shouldRender = index === 0 || index === points.length - 1 || index % xStep === 0;
        if (!shouldRender) return null;
        const x = paddingLeft + (index / (points.length - 1 || 1)) * chartWidth;
        return (
          <text key={point.period} className="detail-chart__tick detail-chart__tick--x" x={x} y={height - 6} textAnchor="middle">
            {point.period}
          </text>
        );
      })}
      <polyline points={coordinates} />
      <text className="detail-chart__axis-label" x={paddingLeft} y={12}>
        {unit}
      </text>
    </svg>
  );
}

function KpiCard({ kpi, onOpen }: { kpi: KpiMetric; onOpen: (detail: DetailState) => void }) {
  const compactTrend = compactTrendForCard(kpi.trend, 28);
  return (
    <button
      type="button"
      className="kpi-card kpi-card--interactive"
      onClick={() =>
        onOpen({
          id: kpi.id,
          title: kpi.label,
          source: kpi.source,
          status: kpi.status,
          value: kpi.value,
          delta: kpi.delta,
          updatedAt: kpi.updatedAt,
          history: buildKpiHistory(kpi),
          unit: inferUnit(kpi.value, kpi.delta, kpi.label)
        })
      }
    >
      <header className="kpi-card__head">
        <p className="kpi-card__label">{kpi.label}</p>
        <span className={sourceClassName(kpi.source)}>{kpi.source}</span>
      </header>
      <p className="kpi-card__value">{kpi.value}</p>
      <p className="kpi-card__delta">{kpi.delta}</p>
      <Sparkline points={compactTrend} />
      <footer className="kpi-card__meta">
        <span>{kpi.updatedAt}</span>
        <span className={statusClassName(kpi.status)}>{kpi.status}</span>
      </footer>
    </button>
  );
}

function SourceSelector({
  source,
  options,
  onChange
}: {
  source: DataSource;
  options: DataSource[];
  onChange?: (source: DataSource) => void;
}) {
  const isSelectable = options.length > 1 && Boolean(onChange);
  if (!isSelectable) return <span className={sourceClassName(source)}>{source}</span>;
  return (
    <select
      className={sourceClassName(source)}
      value={source}
      aria-label="Seleccionar fuente"
      onClick={(event) => event.stopPropagation()}
      onChange={(event) => onChange?.(event.target.value as DataSource)}
    >
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

function MiniSeries({ values }: { values: { period: string; value: number }[] }) {
  const width = 150;
  const height = 44;
  const min = Math.min(...values.map((point) => point.value));
  const max = Math.max(...values.map((point) => point.value));
  const range = max - min || 1;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1 || 1)) * width;
      const normalized = (value.value - min) / range;
      const y = height - normalized * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="mini-series" aria-label="Serie temporal de cinco periodos">
      <svg className="mini-series__line" viewBox={`0 0 ${width} ${height}`} aria-hidden="true" focusable="false">
        <polyline points={points} />
      </svg>
      <div className="mini-series__labels">
        {values.map((point) => (
          <span key={point.period} className="mini-series__label">
            {point.period}
          </span>
        ))}
      </div>
    </div>
  );
}

type CountryOverviewDashboardProps = {
  data?: CountryOverviewData;
};

function isProjectionSection(sectionId: string, sectionTitle: string): boolean {
  const normalizedId = sectionId.toLowerCase();
  const normalizedTitle = sectionTitle.toLowerCase();
  return normalizedId.includes("proyeccion") || normalizedTitle.includes("proyeccion");
}

function removeFutureHistoryPoints(history: HistoryPoint[]): HistoryPoint[] {
  const now = new Date();
  return history.filter((point) => {
    const parsed = parseHistoryDate(point.period);
    if (!parsed) return true;
    return parsed.getTime() <= now.getTime();
  });
}

function sanitizeOverviewForCurrentView(overview: CountryOverviewData): CountryOverviewData {
  const sanitizedKpis = overview.executiveKpis
    .map((kpi) => {
      const history = removeFutureHistoryPoints(buildKpiHistory(kpi));
      if (history.length === 0) return null;
      return {
        ...kpi,
        trend: history.map((point) => point.value),
        updatedAt: history[history.length - 1]?.period ?? kpi.updatedAt
      };
    })
    .filter((kpi): kpi is KpiMetric => Boolean(kpi));

  return {
    ...overview,
    executiveKpis: sanitizedKpis,
    sections: overview.sections
      .filter((section) => !isProjectionSection(section.id, section.title))
      .map((section) => ({
        ...section,
        indicators: section.indicators
          .map((indicator) => {
            const history = removeFutureHistoryPoints(indicator.series);
            if (history.length === indicator.series.length) return indicator;
            const latestPoint = history[history.length - 1];
            return {
              ...indicator,
              series: history,
              period: latestPoint?.period ?? indicator.period
            };
          })
          .filter((indicator) => indicator.series.length > 0)
      }))
  };
}

function resolveConceptKey(id: string, label: string): string {
  const idNormalized = id.toLowerCase();
  const labelNormalized = label.toLowerCase();
  const key = `${idNormalized} ${labelNormalized}`;
  if (key.includes("public-balance") || key.includes("saldo público")) return "saldo-publico";
  if (key.includes("vacantes")) return "vacantes";
  if (key.includes("debt") || key.includes("deuda")) return "deuda-publica";
  if (key.includes("paro") || key.includes("unemployment") || key.includes("desemple")) return "paro";
  if (key.includes("inflation") || key.includes("inflaci") || key.includes("ipc")) return "inflacion";
  if (key.includes("gdp") || key.includes("pib")) return "pib";
  if (key.includes("population") || key.includes("poblaci")) return "poblacion";
  if (key.includes("employment") || key.includes("ocupaci")) return "ocupacion";
  return idNormalized;
}

function collectConceptVariants(overview: CountryOverviewData): Record<string, MetricVariant[]> {
  const variantsByConcept = new Map<string, Map<DataSource, MetricVariant>>();

  for (const kpi of overview.executiveKpis) {
    const conceptKey = resolveConceptKey(kpi.id, kpi.label);
    const conceptMap = variantsByConcept.get(conceptKey) ?? new Map<DataSource, MetricVariant>();
    conceptMap.set(kpi.source, {
      conceptKey,
      source: kpi.source,
      status: kpi.status,
      value: kpi.value,
      delta: kpi.delta,
      updatedAt: kpi.updatedAt,
      history: buildKpiHistory(kpi),
      unit: inferUnit(kpi.value, kpi.delta, kpi.label)
    });
    variantsByConcept.set(conceptKey, conceptMap);
  }

  for (const section of overview.sections) {
    for (const indicator of section.indicators) {
      const conceptKey = resolveConceptKey(indicator.id, indicator.label);
      const conceptMap = variantsByConcept.get(conceptKey) ?? new Map<DataSource, MetricVariant>();
      conceptMap.set(indicator.source, {
        conceptKey,
        source: indicator.source,
        status: indicator.status,
        value: indicator.value,
        delta: indicator.change,
        updatedAt: indicator.period,
        history: indicator.series,
        unit: inferUnit(indicator.value, indicator.change, indicator.label),
        note: indicator.note
      });
      variantsByConcept.set(conceptKey, conceptMap);
    }
  }

  const result: Record<string, MetricVariant[]> = {};
  for (const [conceptKey, mapBySource] of variantsByConcept) {
    const allowed = CONCEPT_ALLOWED_SOURCES[conceptKey];
    const variants = Array.from(mapBySource.values()).filter(
      (variant) => !allowed || allowed.includes(variant.source)
    );
    result[conceptKey] = variants;
  }
  return result;
}

export function CountryOverviewDashboard({ data }: CountryOverviewDashboardProps) {
  const publicApiBase = useMemo(() => {
    const raw = (process.env.NEXT_PUBLIC_STORIES_API_BASE_URL ?? "").replace(/\/$/, "");
    if (!raw) return "";
    if (typeof window === "undefined") return raw;
    try {
      const parsed = new URL(raw);
      // Browser can't resolve Docker-internal hostnames like "api".
      if (parsed.hostname === "api") {
        return `${window.location.protocol}//${window.location.hostname}:8000`;
      }
      return raw;
    } catch {
      return raw;
    }
  }, []);
  const rawOverview = data ?? getCountryOverviewSeedData();
  const overview = useMemo(() => sanitizeOverviewForCurrentView(rawOverview), [rawOverview]);
  const conceptVariants = useMemo(() => collectConceptVariants(overview), [overview]);
  const [selectedSourceByConcept, setSelectedSourceByConcept] = useState<Record<string, DataSource>>({});
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [oecdRanking, setOecdRanking] = useState<OecdRanking | null>(null);
  const [oecdRankingLoading, setOecdRankingLoading] = useState(false);
  const [horizon, setHorizon] = useState<HorizonPreset>("5A");
  const renderedExecutiveKpis = useMemo<RenderedKpiItem[]>(() => {
    return overview.executiveKpis.map((kpi) => {
      const conceptKey = resolveConceptKey(kpi.id, kpi.label);
      const variants = conceptVariants[conceptKey] ?? [];
      const selectedSource = selectedSourceByConcept[conceptKey];
      const activeVariant = variants.find((variant) => variant.source === selectedSource);
      const renderedKpi = activeVariant
        ? {
            ...kpi,
            source: activeVariant.source,
            status: activeVariant.status,
            value: activeVariant.value,
            delta: activeVariant.delta,
            updatedAt: activeVariant.updatedAt,
            trend: activeVariant.history.map((point) => point.value)
          }
        : kpi;
      return {
        conceptKey,
        kpi: renderedKpi,
        history: activeVariant ? activeVariant.history : buildKpiHistory(renderedKpi),
        unit: activeVariant ? activeVariant.unit : inferUnit(renderedKpi.value, renderedKpi.delta, renderedKpi.label),
        note: activeVariant?.note,
        options: variants.map((variant) => variant.source)
      };
    });
  }, [overview.executiveKpis, conceptVariants, selectedSourceByConcept]);
  const detailRows = useMemo(() => {
    if (!detail) return [];
    return filterHistoryByHorizon(detail.history, horizon);
  }, [detail, horizon]);
  const availableHorizons = useMemo(() => {
    if (!detail) return [] as HorizonPreset[];
    const all: HorizonPreset[] = ["1A", "5A", "15A", "30A"];
    const dated = getDatedHistory(detail.history);
    return all.filter(
      (option) => hasRealCoverageForHorizon(dated, option) && filterHistoryByHorizon(detail.history, option, false).length >= 2
    );
  }, [detail]);
  useEffect(() => {
    if (!detail) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDetail(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [detail]);

  useEffect(() => {
    if (!detail) return;
    setHorizon(recommendDefaultHorizon(detail.history));
  }, [detail?.id, detail?.history]);

  useEffect(() => {
    setSelectedSourceByConcept((current) => {
      const next: Record<string, DataSource> = {};
      for (const [conceptKey, variants] of Object.entries(conceptVariants)) {
        if (!variants.length) continue;
        const validSources = variants.map((variant) => variant.source);
        const existing = current[conceptKey];
        next[conceptKey] = existing && validSources.includes(existing) ? existing : validSources[0];
      }
      return next;
    });
  }, [conceptVariants]);

  useEffect(() => {
    if (!availableHorizons.length) return;
    if (!availableHorizons.includes(horizon)) {
      setHorizon(availableHorizons[availableHorizons.length - 1]);
    }
  }, [availableHorizons, horizon]);

  useEffect(() => {
    if (!isOecdDigitalIndex(detail)) {
      setOecdRanking(null);
      setOecdRankingLoading(false);
      return;
    }
    const detailId = detail?.id;
    if (!detailId) return;
    const controller = new AbortController();
    setOecdRankingLoading(true);
    setOecdRanking(null);
    const rankingUrl = `${publicApiBase}/public/country-overview/ranking/${detailId}`;
    fetch(rankingUrl, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload: OecdRanking | null) => {
        setOecdRanking(payload);
      })
      .catch(() => {
        setOecdRanking(null);
      })
      .finally(() => {
        setOecdRankingLoading(false);
      });
    return () => controller.abort();
  }, [detail?.id, publicApiBase]);

  return (
    <div className="country-dashboard">
      <section className="country-hero">
        <p className="pill mb-xs">Ficha país</p>
        <h1 className="mb-sm">España: overview ejecutivo</h1>
        <p className="muted mb-sm">
          Seguimiento macro y estructural con trazabilidad por indicador para lectura rápida de situación, evolución
          y riesgos.
        </p>
      </section>

      <section className="kpi-carousel" aria-label="Indicadores clave de España">
        <div className="kpi-carousel__track">
          {[...renderedExecutiveKpis, ...renderedExecutiveKpis].map((item, index) => (
            <button
              key={`${item.kpi.id}-${index}`}
              type="button"
              className="kpi-card kpi-card--interactive"
              onClick={() =>
                setDetail({
                  id: item.kpi.id,
                  title: item.kpi.label,
                  source: item.kpi.source,
                  status: item.kpi.status,
                  value: item.kpi.value,
                  delta: item.kpi.delta,
                  updatedAt: item.kpi.updatedAt,
                  history: item.history,
                  unit: item.unit,
                  note: item.note
                })
              }
            >
              <header className="kpi-card__head">
                <p className="kpi-card__label">{item.kpi.label}</p>
                <SourceSelector
                  source={item.kpi.source}
                  options={item.options}
                  onChange={(source) =>
                    setSelectedSourceByConcept((current) => ({ ...current, [item.conceptKey]: source }))
                  }
                />
              </header>
              <p className="kpi-card__value">{item.kpi.value}</p>
              <p className="kpi-card__delta">{item.kpi.delta}</p>
              <Sparkline points={compactTrendForCard(item.kpi.trend, 28)} />
              <footer className="kpi-card__meta">
                <span>{item.kpi.updatedAt}</span>
                <span className={statusClassName(item.kpi.status)}>{item.kpi.status}</span>
              </footer>
            </button>
          ))}
        </div>
      </section>

      <section className="card country-insights" aria-label="Lectura rápida">
        <h2>Lectura rápida</h2>
        <ul>
          {overview.executiveNarrative.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className="country-sections" aria-label="Bloques temáticos">
        {overview.sections.map((section) => (
          <article key={section.id} className="card country-section">
            <header className="country-section__header">
              <h2>
                {SECTION_ICONS[section.id] ? (
                  <span aria-hidden="true" style={{ marginRight: "0.45rem" }}>
                    {SECTION_ICONS[section.id]}
                  </span>
                ) : null}
                {section.title}
              </h2>
              <p className="muted">{section.description}</p>
            </header>
            <div className="country-section__grid">
              {section.indicators.map((indicator) => {
                const conceptKey = resolveConceptKey(indicator.id, indicator.label);
                const variants = conceptVariants[conceptKey] ?? [];
                const selectedSource = selectedSourceByConcept[conceptKey];
                const activeVariant = variants.find((variant) => variant.source === selectedSource);
                const renderedIndicator =
                  activeVariant
                    ? {
                        ...indicator,
                        source: activeVariant.source,
                        status: activeVariant.status,
                        value: activeVariant.value,
                        change: activeVariant.delta,
                        period: activeVariant.updatedAt,
                        series: activeVariant.history,
                        note: activeVariant.note ?? indicator.note
                      }
                    : indicator;
                const compactSeries = compactSeriesForCard(renderedIndicator.series, 5);
                return (
                  <button
                    key={indicator.id}
                    type="button"
                    className="country-indicator country-indicator--interactive"
                    onClick={() =>
                      setDetail({
                        id: renderedIndicator.id,
                        title: renderedIndicator.label,
                        source: renderedIndicator.source,
                        status: renderedIndicator.status,
                        value: renderedIndicator.value,
                        delta: renderedIndicator.change,
                        updatedAt: renderedIndicator.period,
                        history: renderedIndicator.series,
                        unit: inferUnit(renderedIndicator.value, renderedIndicator.change, renderedIndicator.label),
                        note: renderedIndicator.note
                      })
                    }
                  >
                    <header className="country-indicator__head">
                      <h3>{renderedIndicator.label}</h3>
                      <SourceSelector
                        source={renderedIndicator.source}
                        options={variants.map((variant) => variant.source)}
                        onChange={(source) => setSelectedSourceByConcept((current) => ({ ...current, [conceptKey]: source }))}
                      />
                    </header>
                    <p className="country-indicator__value">{renderedIndicator.value}</p>
                    <p className="country-indicator__change">{renderedIndicator.change}</p>
                    <MiniSeries values={compactSeries} />
                    <p className="country-indicator__note">{renderedIndicator.note}</p>
                    <footer className="country-indicator__meta">
                      <span>{renderedIndicator.period}</span>
                      <span className={statusClassName(renderedIndicator.status)}>{renderedIndicator.status}</span>
                    </footer>
                  </button>
                );
              })}
            </div>
          </article>
        ))}
      </section>
      {detail ? (
        <div className="series-detail-backdrop" role="presentation" onClick={() => setDetail(null)}>
          <section
            className="series-detail card"
            role="dialog"
            aria-modal="true"
            aria-label={`Detalle de ${detail.title}`}
            onClick={(event) => event.stopPropagation()}
          >
            <header className="series-detail__header">
              <div>
                <h2>{detail.title}</h2>
                <p className="series-detail__meta-compact">
                  <span className={sourceClassName(detail.source)}>{detail.source}</span>
                  <span>Actualizado: {detail.updatedAt}</span>
                </p>
              </div>
              <button type="button" className="btn btn--ghost" onClick={() => setDetail(null)}>
                Cerrar
              </button>
            </header>
            <div className="series-detail__horizons" role="group" aria-label="Horizonte temporal">
              {availableHorizons.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={option === horizon ? "series-detail__horizon is-active" : "series-detail__horizon"}
                  onClick={() => setHorizon(option)}
                >
                  {option}
                </button>
              ))}
            </div>
            {detailRows.length > 1 ? <DetailChart points={detailRows} unit={detail.unit} title={detail.title} /> : null}
            <div className="series-detail__table-wrap">
              <table className="series-detail__table">
                <thead>
                  <tr>
                    <th>Periodo</th>
                    <th>Valor ({detail.unit})</th>
                  </tr>
                </thead>
                <tbody>
                  {detailRows.map((point) => (
                    <tr key={`${detail.id}-${point.period}`}>
                      <td>{point.period}</td>
                      <td>{formatHistoryNumber(point.value, detail.unit, detail.title)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {detail.note ? <p className="series-detail__note">{detail.note}</p> : null}
            {isOecdDigitalIndex(detail) && oecdRankingLoading ? (
              <p className="series-detail__note">Cargando ranking internacional OECD...</p>
            ) : null}
            {isOecdDigitalIndex(detail) && oecdRanking ? (
              <p className="series-detail__note">
                Ranking OECD: Espana {oecdRanking.rank}/{oecdRanking.total_countries}
                {oecdRanking.year ? ` (${oecdRanking.year})` : ""}.
              </p>
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  );
}
