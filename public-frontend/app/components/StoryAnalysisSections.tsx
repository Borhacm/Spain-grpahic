import type { PublicCorrelationItem } from "@/lib/api";

type Props = {
  economic: string;
  social: string;
  correlations: PublicCorrelationItem[];
};

export function StoryAnalysisSections({ economic, social, correlations }: Props) {
  const hasEcon = economic.trim().length > 0;
  const hasSocial = social.trim().length > 0;
  const hasCorr = correlations.length > 0;
  if (!hasEcon && !hasSocial && !hasCorr) {
    return null;
  }

  return (
    <section className="story-analysis" aria-label="Contexto económico y social">
      {hasEcon ? (
        <div className="story-analysis__block">
          <h2 className="story-analysis__heading">Lectura económica</h2>
          <p className="story-analysis__text">{economic}</p>
        </div>
      ) : null}
      {hasSocial ? (
        <div className="story-analysis__block">
          <h2 className="story-analysis__heading">Lectura social</h2>
          <p className="story-analysis__text">{social}</p>
        </div>
      ) : null}
      {hasCorr ? (
        <div className="story-analysis__block">
          <h2 className="story-analysis__heading">Relación con otros datos</h2>
          <ul className="story-analysis__correlations">
            {correlations.map((c, i) => (
              <li key={`${c.series_title}-${i}`}>
                <strong className="story-analysis__series">{c.series_title}</strong>
                {c.coefficient != null && Number.isFinite(c.coefficient) ? (
                  <span className="story-analysis__coef muted">
                    {" "}
                    (correlación aproximada{" "}
                    {c.coefficient.toLocaleString("es-ES", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2
                    })}
                    )
                  </span>
                ) : null}
                <p className="story-analysis__corr-text">{c.comparison_text}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
