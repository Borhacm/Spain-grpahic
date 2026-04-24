import Link from "next/link";

import { StoryMeta } from "@/app/components/StoryMeta";

export type StoryCardProps = {
  slug: string;
  title: string;
  dek?: string | null;
  topic?: string | null;
  tags?: string[] | null;
  publishedAt?: string | null;
};

/**
 * Tarjeta de listado: solo presentación y enlace; sin fetch ni transformación de API.
 */
export function StoryCard({ slug, title, dek, topic, tags, publishedAt }: StoryCardProps) {
  const summary = dek?.trim() || null;

  return (
    <article className="story-card-ed">
      <Link href={`/stories/${encodeURIComponent(slug)}`} className="story-card-ed__link">
        <h2 className="story-card-ed__title font-display">{title}</h2>
        {summary ? <p className="story-card-ed__dek">{summary}</p> : null}
        <StoryMeta topic={topic} tags={tags} publishedAt={publishedAt} layout="card" />
      </Link>
    </article>
  );
}
