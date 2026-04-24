import type { Metadata } from "next";
import Link from "next/link";

import { StoryList } from "@/app/components/StoryList";
import { JsonLd } from "@/components/json-ld";
import { ButtonLink } from "@/components/ui/button";
import { getStories } from "@/lib/api";
import { breadcrumbJsonLd } from "@/lib/jsonld";
import { SITE_NAME } from "@/lib/site";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Últimas historias",
  description: "Historias de datos publicadas: contexto, gráficos y fuentes.",
  alternates: { canonical: "/historias" },
  openGraph: {
    title: `Últimas historias · ${SITE_NAME}`,
    description: "Historias de datos publicadas sobre España.",
    url: "/historias"
  }
};

export default async function HistoriasPage() {
  const { items: stories } = await getStories();
  const topics = Array.from(new Set(stories.map((story) => story.topic).filter(Boolean))) as string[];

  return (
    <section>
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Inicio", path: "/" },
          { name: "Historias", path: "/historias" }
        ])}
      />
      <nav className="breadcrumb" aria-label="Ruta">
        <ButtonLink href="/" variant="inline">
          Inicio
        </ButtonLink>
      </nav>
      <h1 className="mb-sm">Últimas historias</h1>
      <p className="muted mb-md">
        Selección editorial: contexto, gráficos y fuentes verificables.
      </p>
      {topics.length > 0 ? (
        <div className="mb-md">
          <p className="muted mb-xs">Explorar por tema</p>
          <nav className="topic-pills" aria-label="Temas">
            {topics.map((topic) => (
              <Link key={topic} href={`/topics/${encodeURIComponent(topic)}`}>
                {topic}
              </Link>
            ))}
          </nav>
        </div>
      ) : null}
      <StoryList stories={stories} />
    </section>
  );
}
