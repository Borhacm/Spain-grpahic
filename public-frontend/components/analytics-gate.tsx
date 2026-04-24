"use client";

import Script from "next/script";
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "espana_grafico_consent_v1";
const CONSENT_EVENT = "espana-grafico-consent-changed";

function consentAllowsAnalytics(): boolean {
  if (typeof window === "undefined") return false;
  const current = localStorage.getItem(STORAGE_KEY);
  if (current === "all") return true;
  return false;
}

export function AnalyticsGate() {
  const [allow, setAllow] = useState(false);

  const sync = useCallback(() => {
    setAllow(consentAllowsAnalytics());
  }, []);

  useEffect(() => {
    sync();
    window.addEventListener(CONSENT_EVENT, sync);
    return () => {
      window.removeEventListener(CONSENT_EVENT, sync);
    };
  }, [sync]);

  const provider = process.env.NEXT_PUBLIC_ANALYTICS_PROVIDER?.toLowerCase() ?? "none";
  const plausibleDomain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN?.trim();
  const gaId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID?.trim();

  if (!allow) return null;

  if (provider === "plausible" && plausibleDomain) {
    return (
      <Script
        defer
        data-domain={plausibleDomain}
        src="https://plausible.io/js/script.js"
        strategy="afterInteractive"
      />
    );
  }

  if ((provider === "ga4" || provider === "gtag") && gaId) {
    const idJson = JSON.stringify(gaId);
    return (
      <>
        <Script
          src={`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(gaId)}`}
          strategy="afterInteractive"
        />
        <Script id="espana-grafico-ga4" strategy="afterInteractive">
          {`
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', ${idJson}, { anonymize_ip: true });
`}
        </Script>
      </>
    );
  }

  return null;
}
