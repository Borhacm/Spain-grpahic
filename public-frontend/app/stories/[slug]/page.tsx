import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { StoryAnalysisSections } from "@/app/components/StoryAnalysisSections";
import { hasStoryChartSpec, StoryChart } from "@/app/components/StoryChart";
import { StoryHero } from "@/app/components/StoryHero";
import { JsonLd } from "@/components/json-ld";
import { SourceList } from "@/components/source-list";
import { ButtonLink } from "@/components/ui/button";
import { Prose } from "@/components/ui/prose";
import { getStoryBySlug } from "@/lib/api";
import { SITE_NAME } from "@/lib/site";
import { articleJsonLd, breadcrumbJsonLd, type BreadcrumbItem } from "@/lib/jsonld";

type StoryPageProps = { params: Promise<{ slug: string }> };
export const dynamic = "force-dynamic";
/** Resolución de `api` en Docker y fetch a la API editorial (no Edge). */
export const runtime = "nodejs";

function normalizeStorySlug(raw: string): string {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function bodyParagraphs(markdown: string): string[] {
  return markdown
    .trim()
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);
}

export async function generateMetadata({ params }: StoryPageProps): Promise<Metadata> {
  const { slug: rawSlug } = await params;
  const slug = normalizeStorySlug(rawSlug);
  try {
    const story = await getStoryBySlug(slug);
    const description = story.subtitle ?? `Historia de datos publicada en ${SITE_NAME}.`;
    return {
      title: story.title,
      description,
      alternates: { canonical: `/stories/${slug}` },
      openGraph: {
        type: "article",
        locale: "es_ES",
        siteName: SITE_NAME,
        title: story.title,
        description,
        url: `/stories/${slug}`,
        publishedTime: story.published_at ?? undefined,
        modifiedTime: story.updated_at
      },
      twitter: {
        card: "summary_large_image",
        title: story.title,
        description
      }
    };
  } catch {
    return {
      title: "Historia no encontrada"
    };
  }
}

export default async function StoryPage({ params }: StoryPageProps) {
  const { slug: rawSlug } = await params;
  const slug = normalizeStorySlug(rawSlug);
  try {
    const story = await getStoryBySlug(slug);
    const primarySpec = story.primary_chart_spec;
    const secondarySpec = story.secondary_chart_spec;

    const crumbs: BreadcrumbItem[] = [{ name: "Inicio", path: "/" }];
    if (story.topic) {
      crumbs.push({
        name: story.topic,
        path: `/topics/${encodeURIComponent(story.topic)}`
      });
    }
    const titleShort =
      story.title.length > 90 ? `${story.title.slice(0, 87).trimEnd()}…` : story.title;
    crumbs.push({ name: titleShort, path: `/stories/${slug}` });

    const paragraphs = bodyParagraphs(story.body_markdown);

    return (
      <>
        <JsonLd data={articleJsonLd(story)} />
        <JsonLd data={breadcrumbJsonLd(crumbs)} />
        <nav className="breadcrumb" aria-label="Ruta">
          <ButtonLink href="/" variant="inline">
            Inicio
          </ButtonLink>
          {story.topic ? (
            <>
              {" · "}
              <ButtonLink href={`/topics/${encodeURIComponent(story.topic)}`} variant="inline">
                {story.topic}
              </ButtonLink>
            </>
          ) : null}
        </nav>
        <article className="card story-article">
          <StoryHero
            title={story.title}
            subtitle={story.subtitle}
            dek={story.dek}
            topic={story.topic}
            tags={story.tags}
            publishedAt={story.published_at}
          />
          <StoryChart spec={primarySpec} ariaHeadingId="chart-heading-primary" />
          {paragraphs.length > 0 ? (
            <Prose as="section">
              {paragraphs.map((block, i) => (
                <p key={i} className="story-body">
                  {block}
                </p>
              ))}
            </Prose>
          ) : null}
          {hasStoryChartSpec(secondarySpec) ? (
            <StoryChart
              spec={secondarySpec}
              caption="Complemento"
              ariaHeadingId="chart-heading-secondary"
              className="story-chart--spaced"
            />
          ) : null}
          <SourceList sources={story.sources ?? undefined} />
        </article>
      </>
    );
  } catch {
    notFound();
  }
}
