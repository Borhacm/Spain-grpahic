import "./globals.css";
import Link from "next/link";
import type { Metadata } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import type { ReactNode } from "react";

import { AnalyticsGate } from "@/components/analytics-gate";
import { CookieConsentBanner } from "@/components/cookie-consent";
import { SiteFooter } from "@/components/site-footer";
import { getSiteUrl, SITE_NAME } from "@/lib/site";

const sans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap"
});

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap"
});

const siteUrl = getSiteUrl();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: SITE_NAME,
    template: `%s · ${SITE_NAME}`
  },
  description: "Historias de datos sobre España: contexto, gráficos y fuentes verificables.",
  openGraph: {
    type: "website",
    locale: "es_ES",
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: "Historias de datos sobre España."
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_NAME,
    description: "Historias de datos sobre España."
  },
  alternates: {
    canonical: "/",
    types: {
      "application/rss+xml": `${siteUrl}/feed.xml`
    }
  }
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={`${sans.variable} ${display.variable}`}>
      <body>
        <div className="shell">
          <header className="site-header">
            <div className="site-header__inner">
              <Link href="/" className="site-header__brand font-display">
                <span className="site-header__logotype">{SITE_NAME}</span>
              </Link>
              <p className="site-header__tagline">Datos claros sobre economía, clima, empresas y territorio.</p>
            </div>
          </header>
          <main className="shell__main">{children}</main>
          <SiteFooter />
          <CookieConsentBanner />
          <AnalyticsGate />
        </div>
      </body>
    </html>
  );
}
