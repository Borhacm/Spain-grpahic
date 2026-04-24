import type { NextRequest } from "next/server";

const UPSTREAM = (process.env.STORIES_API_BASE_URL ?? "").replace(/\/$/, "");

/**
 * Fachada server-side: el navegador solo llama al mismo origen; la URL del backend
 * FastAPI vive en STORIES_API_BASE_URL (Vercel → Environment, no pública en el bundle).
 */
export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  if (!UPSTREAM) {
    return new Response(
      JSON.stringify({ detail: "STORIES_API_BASE_URL no está configurada en Vercel (entorno de servidor)." }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }

  const { path: segments = [] } = await context.params;
  const subpath = segments.join("/");
  const pathPart = subpath ? `/${subpath}` : "";
  const target = new URL(pathPart, `${UPSTREAM}/`);
  target.search = request.nextUrl.search;

  const res = await fetch(target.toString(), {
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  const body = await res.text();
  return new Response(body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" }
  });
}
