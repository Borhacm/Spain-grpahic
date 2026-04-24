import Link from "next/link";

import { getSiteUrl, SITE_NAME } from "@/lib/site";

export function SiteFooter() {
  const site = getSiteUrl();
  const feedUrl = `${site}/feed.xml`;

  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <nav className="site-footer__nav" aria-label="Pie de página">
          <Link href="/sobre">Sobre {SITE_NAME}</Link>
          <Link href="/metodologia">Metodología</Link>
          <a href={feedUrl}>RSS</a>
        </nav>
        <nav className="site-footer__legal" aria-label="Legal">
          <Link href="/legal/aviso-legal">Aviso legal</Link>
          <Link href="/legal/privacidad">Privacidad</Link>
          <Link href="/legal/privacidad#cookies">Cookies</Link>
        </nav>
        <p className="site-footer__note muted">
          Fachada pública independiente de la consola editorial interna.
        </p>
      </div>
    </footer>
  );
}
