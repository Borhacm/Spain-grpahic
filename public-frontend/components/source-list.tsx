function sourceLabel(row: Record<string, unknown>): string {
  const keys = ["title", "name", "label", "source", "publisher"] as const;
  for (const k of keys) {
    const v = row[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "Fuente";
}

function sourceHref(row: Record<string, unknown>): string | null {
  const keys = ["url", "link", "href"] as const;
  for (const k of keys) {
    const v = row[k];
    if (typeof v === "string" && v.startsWith("http")) return v;
  }
  return null;
}

type Props = { sources: Array<Record<string, unknown>> | null | undefined };

export function SourceList({ sources }: Props) {
  if (!sources?.length) return null;
  return (
    <section className="sources-block" aria-labelledby="sources-heading">
      <h3 id="sources-heading">Fuentes y metadatos</h3>
      <ul className="sources-list">
        {sources.map((row, idx) => {
          const href = sourceHref(row);
          const label = sourceLabel(row);
          return (
            <li key={`${label}-${idx}`} className="sources-list__item">
              {href ? (
                <a href={href} target="_blank" rel="noopener noreferrer">
                  {label}
                </a>
              ) : (
                <span>{label}</span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
