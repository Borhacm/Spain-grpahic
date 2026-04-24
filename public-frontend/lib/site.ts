/** Marca visible en cabecera, metadatos, RSS y JSON-LD. */
export const SITE_NAME = "España en un gráfico";

/**
 * URL pública del sitio (metadata, sitemap, Open Graph, RSS).
 * 1) NEXT_PUBLIC_SITE_URL si está definida (Vercel producción / .env)
 * 2) VERCEL en preview/deploy de Vercel
 * 3) local
 */
export function getSiteUrl(): string {
  const fromEnv = (process.env.NEXT_PUBLIC_SITE_URL ?? "").trim();
  if (fromEnv) {
    return fromEnv.endsWith("/") ? fromEnv.slice(0, -1) : fromEnv;
  }
  const vercel = (process.env.VERCEL_URL ?? "").trim();
  if (vercel) {
    const u = `https://${vercel}`;
    return u.endsWith("/") ? u.slice(0, -1) : u;
  }
  const raw = "http://localhost:3000";
  return raw;
}
