import type { Metadata } from "next";
import { StoryList } from "@/app/components/StoryList";
import { JsonLd } from "@/components/json-ld";
import { ButtonLink } from "@/components/ui/button";
import { getStoriesByTopic } from "@/lib/api";
import { SITE_NAME } from "@/lib/site";
import { breadcrumbJsonLd } from "@/lib/jsonld";

type TopicPageProps = { params: Promise<{ topic: string }> };
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: TopicPageProps): Promise<Metadata> {
  const { topic } = await params;
  const decoded = decodeURIComponent(topic);
  return {
    title: `Tema: ${decoded}`,
    description: `Historias de datos sobre «${decoded}» en ${SITE_NAME}.`,
    alternates: { canonical: `/topics/${encodeURIComponent(decoded)}` },
    openGraph: {
      title: `${decoded} · ${SITE_NAME}`,
      description: `Historias sobre ${decoded}.`,
      url: `/topics/${encodeURIComponent(decoded)}`
    }
  };
}

export default async function TopicPage({ params }: TopicPageProps) {
  const { topic } = await params;
  const decodedTopic = decodeURIComponent(topic);
  const { items: stories } = await getStoriesByTopic(decodedTopic);

  return (
    <section>
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Inicio", path: "/" },
          { name: decodedTopic, path: `/topics/${encodeURIComponent(decodedTopic)}` }
        ])}
      />
      <nav className="breadcrumb" aria-label="Ruta">
        <ButtonLink href="/" variant="inline">
          Inicio
        </ButtonLink>
      </nav>
      <h1>Historias sobre: {decodedTopic}</h1>
      <p className="muted mb-md">Selección editorial del mismo tema.</p>
      <StoryList stories={stories} emptyLabel="No hay historias para este tema." />
    </section>
  );
}
