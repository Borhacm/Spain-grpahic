import { NextResponse } from "next/server";

import { getStories } from "@/lib/api";
import { getSiteUrl, SITE_NAME } from "@/lib/site";
import { escapeXml } from "@/lib/xml-escape";

export const dynamic = "force-dynamic";

function rfc822Date(iso: string | undefined | null): string {
  if (!iso) return new Date().toUTCString();
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return new Date().toUTCString();
  return d.toUTCString();
}

export async function GET() {
  const site = getSiteUrl();
  let stories: Awaited<ReturnType<typeof getStories>>["items"] = [];
  try {
    const res = await getStories({ page: 1, page_size: 200 });
    stories = res.items;
  } catch {
    stories = [];
  }

  const itemsXml = stories
    .map((story) => {
      const link = `${site}/stories/${story.slug}`;
      const desc = story.summary ?? story.subtitle ?? "";
      const pub = rfc822Date(story.published_at ?? story.updated_at);
      return `    <item>
      <title>${escapeXml(story.title)}</title>
      <link>${escapeXml(link)}</link>
      <guid isPermaLink="true">${escapeXml(link)}</guid>
      <pubDate>${pub}</pubDate>
      <description>${escapeXml(desc)}</description>
    </item>`;
    })
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${escapeXml(SITE_NAME)}</title>
    <link>${escapeXml(site)}</link>
    <description>Historias de datos sobre España</description>
    <language>es-es</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${escapeXml(`${site}/feed.xml`)}" rel="self" type="application/rss+xml" />
${itemsXml}
  </channel>
</rss>`;

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600"
    }
  });
}
