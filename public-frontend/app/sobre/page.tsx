import type { Metadata } from "next";

import { JsonLd } from "@/components/json-ld";
import { Prose } from "@/components/ui/prose";
import { getSiteUrl, SITE_NAME } from "@/lib/site";

const DESCRIPTION = `Qué es la fachada pública ${SITE_NAME} y cómo se relaciona con el trabajo editorial.`;

export const metadata: Metadata = {
  title: `Sobre ${SITE_NAME}`,
  description: DESCRIPTION,
  alternates: { canonical: "/sobre" },
  openGraph: {
    title: `Sobre ${SITE_NAME}`,
    description: "Qué es la fachada pública y el enfoque editorial.",
    url: "/sobre"
  }
};

export default function SobrePage() {
  const site = getSiteUrl();
  const webPageLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: `Sobre ${SITE_NAME}`,
    description: DESCRIPTION,
    url: `${site}/sobre`,
    isPartOf: { "@type": "WebSite", name: SITE_NAME, url: site }
  };

  return (
    <>
      <JsonLd data={webPageLd} />
      <article className="card">
        <h1>Sobre {SITE_NAME}</h1>
        <Prose as="div">
          <p>
            <strong>{SITE_NAME}</strong> es la <strong>fachada pública</strong> de una plataforma editorial centrada en
            datos sobre España: economía, territorio, clima, empresas y políticas públicas, explicados con claridad y
            rigor.
          </p>
          <p>
            Lo que ves aquí son <strong>historias ya publicadas</strong>: texto, metadatos editoriales, sugerencias de
            tipo de gráfico y, cuando hay datos enlazados, una vista previa de la serie subyacente. La producción y el
            control de calidad siguen ocurriendo en un flujo editorial interno separado de esta web.
          </p>
          <p>
            El objetivo es el mismo que el de buen periodismo de datos: que cualquier lector pueda entender{" "}
            <em>qué ha pasado</em>, <em>por qué importa</em> y <em>de dónde salen los números</em>.
          </p>
        </Prose>
      </article>
    </>
  );
}
