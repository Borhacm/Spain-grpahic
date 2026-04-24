import { StoryCard } from "@/app/components/StoryCard";
import type { PublicStoryListItem } from "@/lib/api";

export type StoryListProps = {
  stories: PublicStoryListItem[];
  /** Mensaje cuando no hay elementos (la página puede omitirlo y no renderizar la lista). */
  emptyLabel?: string | null;
};

function pickDek(story: PublicStoryListItem): string | null {
  const raw = story.dek ?? story.subtitle ?? story.summary ?? null;
  return raw?.trim() || null;
}

/**
 * Listado homogéneo de historias para portada, tema y bloques «Lo último».
 */
export function StoryList({ stories, emptyLabel }: StoryListProps) {
  if (stories.length === 0) {
    return emptyLabel ? <p className="story-list__empty muted">{emptyLabel}</p> : null;
  }

  return (
    <div className="story-list">
      {stories.map((story) => (
        <StoryCard
          key={story.id}
          slug={story.slug}
          title={story.title}
          dek={pickDek(story)}
          topic={story.topic}
          tags={story.tags}
          publishedAt={story.published_at ?? null}
        />
      ))}
    </div>
  );
}
