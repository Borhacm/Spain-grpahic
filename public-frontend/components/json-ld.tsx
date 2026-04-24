type JsonLdProps = { data: Record<string, unknown> };

/** Datos estructurados para buscadores (JSON-LD). */
export function JsonLd({ data }: JsonLdProps) {
  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
  );
}
