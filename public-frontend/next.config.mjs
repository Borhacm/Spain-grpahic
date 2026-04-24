import path from "node:path";
import { fileURLToPath } from "node:url";

const dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Inyecta la ruta pública hacia /api/spain-backend (mismo origen, sin CORS con dominio custom).
 * El backend real va en STORIES_API_BASE_URL (servidor) — ver route.ts.
 */
function injectPublicApiBase() {
  if (process.env.NEXT_PUBLIC_STORIES_API_BASE_URL?.trim()) {
    return {};
  }
  const site = (process.env.NEXT_PUBLIC_SITE_URL ?? "").trim().replace(/\/$/, "");
  if (site) {
    return { NEXT_PUBLIC_STORIES_API_BASE_URL: `${site}/api/spain-backend` };
  }
  if (process.env.VERCEL && process.env.VERCEL_URL) {
    const u = `https://${process.env.VERCEL_URL}`.replace(/\/$/, "");
    return { NEXT_PUBLIC_STORIES_API_BASE_URL: `${u}/api/spain-backend` };
  }
  return {};
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: dirname,
  env: injectPublicApiBase()
};

export default nextConfig;
