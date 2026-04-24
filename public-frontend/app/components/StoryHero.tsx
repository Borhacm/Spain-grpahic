import { StoryMeta } from "@/app/components/StoryMeta";

export type StoryHeroProps = {
  title: string;
  subtitle?: string | null;
  dek?: string | null;
  topic?: string | null;
  tags?: string[] | null;
  publishedAt?: string | null;
};

/**
 * Cabecera editorial para la ficha de historia: título dominante, bajada y meta
 * (fecha, tema, etiquetas) sin aspecto de panel de control.
 */
export function StoryHero({ title, subtitle, dek, topic, tags, publishedAt }: StoryHeroProps) {
  const standfirst = dek?.trim() || subtitle?.trim() || null;

  return (
    <header className="story-hero">
      <h1 className="story-hero__title font-display">{title}</h1>
      {standfirst ? <p className="story-hero__dek">{standfirst}</p> : null}
      <StoryMeta topic={topic} tags={tags} publishedAt={publishedAt} layout="hero" />
    </header>
  );
}
