import type { Metadata } from "next";
import Link from "next/link";
import { StoryList } from "@/app/components/StoryList";
import { JsonLd } from "@/components/json-ld";
import { getStories } from "@/lib/api";
import { SITE_NAME } from "@/lib/site";
import { websiteJsonLd } from "@/lib/jsonld";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Últimas historias",
  description: "Historias de datos publicadas: contexto, gráficos y fuentes.",
  alternates: { canonical: "/" },
  openGraph: {
    title: `Últimas historias · ${SITE_NAME}`,
    description: "Historias de datos publicadas sobre España.",
    url: "/"
  }
};

export default async function HomePage() {
  const { items: stories } = await getStories();
  const topics = Array.from(new Set(stories.map((story) => story.topic).filter(Boolean))) as string[];

  return (
    <section>
      <JsonLd data={websiteJsonLd()} />
      <h1 className="mb-sm">Últimas historias</h1>
      <p className="muted mb-md">
        Frontend público desacoplado de la consola editorial interna.
      </p>
      <article className="card country-overview-entry">
        <h2 className="mb-xs">Ficha país España</h2>
        <p className="muted mb-sm">
          Nueva vista ejecutiva con indicadores clave, bloques temáticos y trazabilidad por fuente oficial.
        </p>
        <Link href="/espana" className="btn btn--primary">
          Abrir dashboard país
        </Link>
      </article>
      {topics.length > 0 ? (
        <div>
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
