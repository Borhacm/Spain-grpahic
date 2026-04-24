import { formatDate } from "@/lib/format-date";

export type StoryMetaProps = {
  topic?: string | null;
  tags?: string[] | null;
  publishedAt?: string | null;
  /** `hero`: cabecera de ficha. `card`: fecha+tema arriba, tags en línea siguiente en listados. */
  layout?: "default" | "hero" | "card";
};

export function StoryMeta({ topic, tags, publishedAt, layout = "default" }: StoryMetaProps) {
  const hasDate = Boolean(publishedAt);
  const hasTopic = Boolean(topic?.trim());
  const tagList = tags?.filter(Boolean) ?? [];

  if (!hasDate && !hasTopic && tagList.length === 0) {
    return null;
  }

  const rootClass =
    layout === "hero"
      ? "story-meta story-meta--hero"
      : layout === "card"
        ? "story-meta story-meta--card"
        : "story-meta";

  return (
    <div className={rootClass}>
      {hasDate ? (
        <time className="story-meta__date" dateTime={publishedAt!}>
          {formatDate(publishedAt!)}
        </time>
      ) : null}
      {hasTopic ? (
        <span className="story-meta__topic" data-role="topic">
          {topic}
        </span>
      ) : null}
      {tagList.length > 0 ? (
        <ul className="story-meta__tags" aria-label="Etiquetas">
          {tagList.map((tag) => (
            <li key={tag}>{tag}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
