import { ImageResponse } from "next/og";

import { SITE_NAME } from "@/lib/site";

export const alt = SITE_NAME;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: 24,
          padding: 64,
          background: "linear-gradient(135deg, #fafbfc 0%, #e2e8f0 55%, #cbd5e1 100%)",
          color: "#0f172a",
          fontFamily: "ui-sans-serif, system-ui, sans-serif"
        }}
      >
        <div style={{ fontSize: 26, fontWeight: 600, letterSpacing: "0.1em", color: "#2563eb" }}>
          {SITE_NAME.toUpperCase()}
        </div>
        <div style={{ fontSize: 64, fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1.05 }}>
          Datos que cuentan España
        </div>
        <div style={{ fontSize: 28, color: "#475569", maxWidth: 820, lineHeight: 1.4 }}>
          Historias editoriales con contexto, gráficos y fuentes.
        </div>
      </div>
    ),
    { ...size }
  );
}
