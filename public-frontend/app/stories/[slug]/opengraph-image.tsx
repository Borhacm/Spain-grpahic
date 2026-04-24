import { ImageResponse } from "next/og";

import { getStoryBySlug } from "@/lib/api";
import { SITE_NAME } from "@/lib/site";

export const runtime = "nodejs";

export const alt = `${SITE_NAME} — vista previa de la historia`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug: rawSlug } = await params;
  const slug = decodeURIComponent(rawSlug);
  let title = SITE_NAME;
  let subtitle = "Historia de datos";
  try {
    const story = await getStoryBySlug(slug);
    title = story.title.length > 110 ? `${story.title.slice(0, 107)}…` : story.title;
    const raw = story.subtitle ?? story.topic ?? "";
    subtitle = raw.length > 100 ? `${raw.slice(0, 97)}…` : raw || "España en datos";
  } catch {
    subtitle = slug.replace(/-/g, " ");
  }

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 56,
          background: "linear-gradient(145deg, #0f172a 0%, #1e3a5f 45%, #2563eb 100%)",
          color: "#f8fafc",
          fontFamily: "ui-sans-serif, system-ui, sans-serif"
        }}
      >
        <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "0.1em", opacity: 0.85 }}>
          {SITE_NAME.toUpperCase()}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 56, fontWeight: 700, lineHeight: 1.12, letterSpacing: "-0.03em" }}>{title}</div>
          <div style={{ fontSize: 28, opacity: 0.92, maxWidth: 900, lineHeight: 1.35 }}>{subtitle}</div>
        </div>
        <div style={{ fontSize: 22, opacity: 0.75 }}>{SITE_NAME} · datos claros</div>
      </div>
    ),
    { ...size }
  );
}
