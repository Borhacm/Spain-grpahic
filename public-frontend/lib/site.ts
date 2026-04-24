/** Marca visible en cabecera, metadatos, RSS y JSON-LD. */
export const SITE_NAME = "España en un gráfico";

/** URL pública del sitio (fachada), para metadata, sitemap y Open Graph. */
export function getSiteUrl(): string {
  const raw = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}
