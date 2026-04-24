import type { MetadataRoute } from "next";

import { getStories } from "@/lib/api";
import { getSiteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = getSiteUrl();
  const entries: MetadataRoute.Sitemap = [
    {
      url: base,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1
    },
    {
      url: `${base}/sobre`,
      changeFrequency: "monthly",
      priority: 0.45
    },
    {
      url: `${base}/metodologia`,
      changeFrequency: "monthly",
      priority: 0.45
    },
    {
      url: `${base}/legal/aviso-legal`,
      changeFrequency: "yearly",
      priority: 0.35
    },
    {
      url: `${base}/legal/privacidad`,
      changeFrequency: "yearly",
      priority: 0.35
    }
  ];

  try {
    const { items: stories } = await getStories({ page: 1, page_size: 500 });
    for (const story of stories) {
      entries.push({
        url: `${base}/stories/${story.slug}`,
        lastModified: story.updated_at
          ? new Date(story.updated_at)
          : story.published_at
            ? new Date(story.published_at)
            : undefined,
        changeFrequency: "weekly",
        priority: 0.75
      });
    }
    const topics = new Set(
      stories.map((s) => s.topic).filter((t): t is string => typeof t === "string" && t.length > 0)
    );
    for (const topic of topics) {
      entries.push({
        url: `${base}/topics/${encodeURIComponent(topic)}`,
        changeFrequency: "weekly",
        priority: 0.55
      });
    }
  } catch {
    /* API no disponible en build o arranque aislado */
  }

  return entries;
}
