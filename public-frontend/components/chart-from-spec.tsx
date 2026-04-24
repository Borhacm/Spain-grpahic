import {
  chartPolicy,
  chartRationale,
  chartTypeLabel,
  parsePreviewPoints,
  prefersBarChart,
  seriesCaption,
} from "@/lib/chart-spec";

type Props = {
  spec: Record<string, unknown>;
  /** Único por página si hay varios `ChartFromSpec` (p. ej. principal + secundario). */
  ariaHeadingId?: string;
  /** Descripción accesible; si existe, se oculta la racionalización técnica del spec. */
  publicCaption?: string;
};

const W = 720;
const H = 280;
const PAD = { top: 20, right: 16, bottom: 36, left: 48 };

function LineChart({ points }: { points: { date: string; value: number }[] }) {
  const values = points.map((p) => p.value);
  const minY = Math.min(...values);
  const maxY = Math.max(...values);
  const spanY = maxY - minY || 1;
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const denom = Math.max(points.length - 1, 1);
  const coords = points.map((p, i) => {
    const x = PAD.left + (innerW * i) / denom;
    const y = PAD.top + innerH - ((p.value - minY) / spanY) * innerH;
    return `${x},${y}`;
  });
  const poly = coords.join(" ");
  const first = points[0];
  const last = points[points.length - 1];

  return (
    <svg
      className="chart-svg"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Vista previa de la serie en el tiempo"
    >
      <rect x="0" y="0" width={W} height={H} fill="var(--chart-bg)" rx="8" />
      <text x={PAD.left} y={16} fill="var(--muted)" fontSize="11">
        {points.length > 1 ? `${first.date} → ${last.date}` : first.date}
      </text>
      {points.length > 1 ? (
        <polyline
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={poly}
        />
      ) : null}
      {points.map((p, i) => {
        const x = PAD.left + (innerW * i) / denom;
        const y = PAD.top + innerH - ((p.value - minY) / spanY) * innerH;
        return <circle key={`${p.date}-${i}`} cx={x} cy={y} r={points.length === 1 ? 5 : 3} fill="var(--accent-strong)" />;
      })}
      <text x={PAD.left} y={H - 10} fill="var(--muted)" fontSize="11">
        Mín. {minY.toLocaleString("es-ES", { maximumFractionDigits: 2 })} · Máx.{" "}
        {maxY.toLocaleString("es-ES", { maximumFractionDigits: 2 })}
      </text>
    </svg>
  );
}

function BarChart({ points }: { points: { date: string; value: number }[] }) {
  const values = points.map((p) => p.value);
  const minY = Math.min(0, ...values);
  const maxY = Math.max(...values);
  const spanY = maxY - minY || 1;
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const barW = innerW / points.length - 4;

  return (
    <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Comparativa por periodo">
      <rect x="0" y="0" width={W} height={H} fill="var(--chart-bg)" rx="8" />
      {points.map((p, i) => {
        const x = PAD.left + (innerW * i) / points.length + 2;
        const barH = ((p.value - minY) / spanY) * innerH;
        const y = PAD.top + innerH - barH;
        return (
          <rect
            key={p.date}
            x={x}
            y={y}
            width={Math.max(barW, 4)}
            height={Math.max(barH, 1)}
            fill="var(--accent)"
            rx="2"
          />
        );
      })}
    </svg>
  );
}

export function ChartFromSpec({
  spec,
  ariaHeadingId = "chart-heading",
  publicCaption,
}: Props) {
  const type = chartTypeLabel(spec);
  const rationale = chartRationale(spec);
  const policy = chartPolicy(spec);
  const series = seriesCaption(spec);
  const points = parsePreviewPoints(spec);
  const useBars = prefersBarChart(type) && points.length >= 2 && points.length <= 24;
  const caption = publicCaption?.trim();
  const showTechnicalRationale = Boolean(rationale) && !caption;

  return (
    <section className="chart-block" aria-labelledby={ariaHeadingId}>
      <div className="chart-block__head">
        <h3 id={ariaHeadingId}>Gráfico</h3>
        <div className="chart-block__meta">
          {type ? <span className="pill">{type}</span> : null}
          {policy ? <span className="pill pill--soft">{policy}</span> : null}
        </div>
      </div>
      {series ? <p className="muted chart-block__series">{series}</p> : null}
      {caption ? <p className="chart-block__public-lede">{caption}</p> : null}
      {showTechnicalRationale ? <p className="chart-block__rationale muted">{rationale}</p> : null}
      {points.length >= 1 ? (
        useBars && points.length >= 2 ? (
          <BarChart points={points} />
        ) : (
          <LineChart points={points} />
        )
      ) : (
        <div className="chart-block__empty muted">
          Sin serie numérica embebida en esta historia. El equipo editorial sigue definiendo la vista de datos
          pública.
        </div>
      )}
    </section>
  );
}
