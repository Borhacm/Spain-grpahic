import type { Metadata } from "next";

import { JsonLd } from "@/components/json-ld";
import { Prose } from "@/components/ui/prose";
import { getSiteUrl, SITE_NAME } from "@/lib/site";

const DESCRIPTION =
  "Cómo pasamos de señales y candidatos editoriales a historias publicadas con gráficos y fuentes.";

export const metadata: Metadata = {
  title: "Metodología",
  description: DESCRIPTION,
  alternates: { canonical: "/metodologia" },
  openGraph: {
    title: `Metodología · ${SITE_NAME}`,
    description: DESCRIPTION,
    url: "/metodologia"
  }
};

export default function MetodologiaPage() {
  const site = getSiteUrl();
  const webPageLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Metodología",
    description: DESCRIPTION,
    url: `${site}/metodologia`,
    isPartOf: { "@type": "WebSite", name: SITE_NAME, url: site }
  };

  return (
    <>
      <JsonLd data={webPageLd} />
      <article className="card">
        <h1>Metodología</h1>
        <Prose as="div">
          <p>
            Detrás de cada historia hay un <strong>pipeline editorial</strong>: detección de señales en series de
            datos, formación de candidatos, puntuación, borradores asistidos y revisión humana (aprobar, descartar o
            enviar a publicación).
          </p>
          <p>
            La recomendación de tipo de gráfico sigue una <strong>política editorial por temas</strong> (economía,
            vivienda, clima, empresas, etc.) y deja constancia del razonamiento en los metadatos de la historia. Cuando
            existe una serie vinculada al candidato, la publicación puede incluir <strong>puntos de vista previa</strong>{" "}
            para que la fachada pueda mostrar una tendencia sin llamadas adicionales a la API de datos.
          </p>
          <p>
            Las <strong>fuentes</strong> listadas en cada pieza son las que el equipo editorial considera relevantes
            para la trazabilidad del dato. Si falta un enlace explícito, la historia puede seguir enlazando a datasets
            o series en capas internas; la fachada prioriza lo que el JSON público expone.
          </p>
          <h2>Cookies, consentimiento y analítica</h2>
          <p>
            La fachada muestra un <strong>banner de cookies</strong> en el primer acceso. Hasta que el visitante
            acepte medición no esencial, no se cargan scripts de analítica de terceros. La elección se guarda en el
            navegador (localStorage) con la clave <code>espana_grafico_consent_v1</code>; puede borrarla desde las
            herramientas de desarrollo del navegador o la configuración de privacidad del mismo dominio.
          </p>
          <p>
            En despliegue, el Titular puede activar <strong>Plausible Analytics</strong> o <strong>Google Analytics
            4</strong> mediante variables de entorno (véase <code>.env.example</code> en el repositorio). La política
            de privacidad describe finalidades y bases legales; la metodología editorial no sustituye el asesoramiento
            jurídico externo.
          </p>
        </Prose>
      </article>
    </>
  );
}
