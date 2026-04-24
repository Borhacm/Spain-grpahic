export type PreviewPoint = { date: string; value: number };

export function parsePreviewPoints(spec: Record<string, unknown> | null | undefined): PreviewPoint[] {
  if (!spec || typeof spec !== "object") return [];
  const out: PreviewPoint[] = [];

  const raw = spec.preview_points;
  if (Array.isArray(raw)) {
    for (const item of raw) {
      if (!item || typeof item !== "object") continue;
      const rec = item as Record<string, unknown>;
      const date = typeof rec.date === "string" ? rec.date : null;
      const value = typeof rec.value === "number" ? rec.value : Number(rec.value);
      if (!date || Number.isNaN(value)) continue;
      out.push({ date, value });
    }
    if (out.length) return out;
  }

  const series = spec.series;
  if (!Array.isArray(series)) return [];
  const first = series[0];
  if (!first || typeof first !== "object") return [];
  const pts = (first as Record<string, unknown>).points;
  if (!Array.isArray(pts)) return [];
  for (const item of pts) {
    if (!item || typeof item !== "object") continue;
    const rec = item as Record<string, unknown>;
    const x = typeof rec.x === "string" || typeof rec.x === "number" ? String(rec.x) : null;
    const yRaw = rec.y;
    const value = typeof yRaw === "number" ? yRaw : Number(yRaw);
    if (!x || Number.isNaN(value)) continue;
    out.push({ date: x, value });
  }
  return out;
}

export function chartTypeLabel(spec: Record<string, unknown> | null | undefined): string | null {
  if (!spec) return null;
  const t = spec.chart_type ?? spec.type;
  return typeof t === "string" && t.length > 0 ? t : null;
}

export function chartRationale(spec: Record<string, unknown> | null | undefined): string | null {
  if (!spec) return null;
  const r = spec.chart_rationale;
  return typeof r === "string" && r.length > 0 ? r : null;
}

export function chartPolicy(spec: Record<string, unknown> | null | undefined): string | null {
  if (!spec) return null;
  const p = spec.chart_policy;
  return typeof p === "string" && p.length > 0 ? p : null;
}

export function seriesCaption(spec: Record<string, unknown> | null | undefined): string | null {
  if (!spec) return null;
  const name = spec.series_name;
  if (typeof name === "string" && name.length > 0) return name;
  const series = spec.series;
  if (Array.isArray(series) && series[0] && typeof series[0] === "object") {
    const label = (series[0] as Record<string, unknown>).label;
    if (typeof label === "string" && label.length > 0) return label;
  }
  const id = spec.series_id;
  if (typeof id === "number") return `Serie #${id}`;
  return null;
}

export function prefersBarChart(chartType: string | null): boolean {
  if (!chartType) return false;
  const t = chartType.toLowerCase();
  return t.includes("bar") || t.includes("column") || t.includes("ranking");
}
