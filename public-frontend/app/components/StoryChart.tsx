import { ChartFromSpec } from "@/components/chart-from-spec";

export type StoryChartProps = {
  spec: Record<string, unknown> | null | undefined;
  /** Leyenda breve encima del bloque (p. ej. gráfico complementario). */
  caption?: string | null;
  /** Texto en lenguaje claro sobre qué muestra el gráfico (público general). */
  publicCaption?: string | null;
  /** Identificador único del título accesible dentro de `ChartFromSpec` (obligatorio si hay dos gráficos en la misma página). */
  ariaHeadingId?: string;
  className?: string | null;
};

function isUsableSpec(spec: unknown): spec is Record<string, unknown> {
  return Boolean(spec && typeof spec === "object" && Object.keys(spec as object).length > 0);
}

/**
 * Contenedor del gráfico en la ficha pública; delega el render en ChartFromSpec.
 */
export function StoryChart({ spec, caption, publicCaption, ariaHeadingId, className }: StoryChartProps) {
  if (!isUsableSpec(spec)) {
    return null;
  }
  const figureClass = ["story-chart", className].filter(Boolean).join(" ");
  return (
    <figure className={figureClass}>
      {caption ? <figcaption className="story-chart__caption">{caption}</figcaption> : null}
      <ChartFromSpec
        spec={spec}
        ariaHeadingId={ariaHeadingId}
        publicCaption={publicCaption ?? undefined}
      />
    </figure>
  );
}

export function hasStoryChartSpec(spec: unknown): boolean {
  return isUsableSpec(spec);
}
