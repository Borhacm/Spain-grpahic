"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "espana_grafico_consent_v1";
const CONSENT_EVENT = "espana-grafico-consent-changed";

export type ConsentValue = "essential" | "all";

function normalizeConsent(raw: string | null): ConsentValue | null {
  if (raw === "essential" || raw === "all") return raw;
  return null;
}

function readConsent(): ConsentValue | null {
  if (typeof window === "undefined") return null;
  const current = normalizeConsent(localStorage.getItem(STORAGE_KEY));
  if (current) return current;

  return null;
}

function writeConsent(value: ConsentValue) {
  localStorage.setItem(STORAGE_KEY, value);
  window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: value }));
}

export function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(readConsent() === null);
  }, []);

  const choose = useCallback((value: ConsentValue) => {
    writeConsent(value);
    setVisible(false);
  }, []);

  if (!visible) return null;

  return (
    <div className="cookie-bar" role="dialog" aria-labelledby="cookie-bar-title" aria-live="polite">
      <div className="cookie-bar__inner">
        <h2 id="cookie-bar-title" className="cookie-bar__title">
          Cookies y medición de audiencia
        </h2>
        <p className="cookie-bar__text">
          Usamos cookies estrictamente necesarias para el funcionamiento del sitio. Si lo autoriza, cargaremos
          herramientas de analítica (por ejemplo Plausible o Google Analytics) según la configuración del entorno, para
          conocer de forma agregada el uso del sitio. Puede cambiar de opinión borrando el almacenamiento local del
          dominio o contactándonos. Más información en nuestra{" "}
          <Link href="/legal/privacidad">política de privacidad</Link>.
        </p>
        <div className="cookie-bar__actions">
          <button type="button" className="btn btn--ghost" onClick={() => choose("essential")}>
            Solo necesarias
          </button>
          <button type="button" className="btn btn--primary" onClick={() => choose("all")}>
            Aceptar y continuar
          </button>
        </div>
      </div>
    </div>
  );
}
