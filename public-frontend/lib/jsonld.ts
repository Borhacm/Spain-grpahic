import type { PublicStoryDetail } from "@/lib/api";

import { getSiteUrl, SITE_NAME } from "@/lib/site";

export function articleJsonLd(story: PublicStoryDetail): Record<string, unknown> {
  const site = getSiteUrl();
  const url = `${site}/stories/${story.slug}`;
  const payload: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: story.title,
    description: story.subtitle ?? story.body_markdown?.slice(0, 220) ?? undefined,
    inLanguage: "es-ES",
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": url
    },
    url
  };
  if (story.published_at) {
    payload.datePublished = story.published_at;
  }
  if (story.updated_at) {
    payload.dateModified = story.updated_at;
  }
  if (story.topic) {
    payload.articleSection = story.topic;
  }
  if (story.tags?.length) {
    payload.keywords = story.tags.join(", ");
  }
  const publisher = {
    "@type": "Organization",
    name: SITE_NAME,
    url: site
  };
  payload.publisher = publisher;
  return payload;
}

export type BreadcrumbItem = { name: string; path: string };

/** Migas de pan para buscadores (Schema.org BreadcrumbList). */
export function breadcrumbJsonLd(items: BreadcrumbItem[]): Record<string, unknown> {
  const site = getSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => {
      const path = item.path.startsWith("/") ? item.path : `/${item.path}`;
      return {
        "@type": "ListItem",
        position: index + 1,
        name: item.name,
        item: `${site}${path}`
      };
    })
  };
}

export function websiteJsonLd(): Record<string, unknown> {
  const site = getSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: site,
    description: "Historias de datos sobre España: contexto, gráficos y fuentes verificables.",
    inLanguage: "es-ES"
  };
}
