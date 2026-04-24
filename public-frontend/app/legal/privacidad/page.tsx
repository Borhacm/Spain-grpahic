import type { Metadata } from "next";

import { LegalEntityBlock } from "@/components/legal-entity-block";
import { Prose } from "@/components/ui/prose";
import { parseLegalEntity } from "@/lib/legal-config";
import { SITE_NAME } from "@/lib/site";

const DESCRIPTION = `Información sobre el tratamiento de datos personales y cookies en el sitio ${SITE_NAME} (RGPD y LSSI-CE).`;

export const metadata: Metadata = {
  title: "Privacidad",
  description: DESCRIPTION,
  alternates: { canonical: "/legal/privacidad" },
  openGraph: {
    title: `Privacidad · ${SITE_NAME}`,
    description: DESCRIPTION,
    url: "/legal/privacidad"
  }
};

export default function PrivacidadPage() {
  const entity = parseLegalEntity();

  return (
    <article className="card">
      <h1>Política de privacidad</h1>
      <LegalEntityBlock entity={entity} />
      <Prose as="div" className="legal-doc">
        <h2>Responsable del tratamiento</h2>
        <p>
          El responsable del tratamiento de los datos personales obtenidos a través del Sitio es el Titular identificado
          al inicio de este documento. Si tiene dudas sobre esta política o sobre el ejercicio de sus derechos, puede
          contactar en la dirección de correo indicada.
        </p>

        <h2>Finalidades, base legal y conservación</h2>
        <ul>
          <li>
            <strong>Navegación y seguridad del Sitio.</strong> Gestionar el acceso, la seguridad técnica y la
            prevención de abusos. Base legal: interés legítimo (art. 6.1.f RGPD) y, en su caso, ejecución de medidas
            precontractuales a petición del interesado. Conservación: plazos técnicos habituales en registros de
            servidor, salvo obligación legal de conservación mayor.
          </li>
          <li>
            <strong>Medición de audiencia (analítica).</strong> Si usted acepta las cookies no esenciales mediante el
            banner del Sitio, podrán cargarse herramientas de analítica configuradas en el entorno (por ejemplo
            Plausible Analytics o Google Analytics 4) para elaborar estadísticas agregadas de uso. Base legal: consentimiento
            (art. 6.1.a RGPD). Conservación: según la política del proveedor y la configuración aplicada.
          </li>
          <li>
            <strong>Comunicaciones.</strong> Atender solicitudes que nos dirija por correo electrónico. Base legal:
            interés legítimo o, según el caso, consentimiento o relación contractual. Conservación: el tiempo necesario
            para atender su petición y los plazos legales aplicables.
          </li>
        </ul>

        <h2>Destinatarios y encargados del tratamiento</h2>
        <p>
          No se prevén cesiones de datos a terceros salvo obligación legal. El Titular podrá recurrir a proveedores de
          servicios (alojamiento, CDN, analítica, correo) que actúen como encargados del tratamiento, con las garantías
          contractuales exigidas por el art. 28 RGPD.
        </p>
        <p>
          Si se utilizan herramientas con soporte fuera del Espacio Económico Europeo, se aplicarán las garantías
          previstas en el RGPD (decisiones de adecuación, cláusulas tipo u otras medidas complementarias).
        </p>

        <h2>Derechos de las personas interesadas</h2>
        <p>Puede ejercer los derechos de acceso, rectificación, supresión, limitación, oposición y portabilidad cuando
          proceda, así como retirar el consentimiento prestado, dirigiendo un correo al responsable indicando el derecho
          que desea ejercer y acreditando su identidad de forma razonable.
        </p>

        <h2>Reclamación ante la autoridad de control</h2>
        <p>
          Si considera que el tratamiento de sus datos personales vulnera la normativa, tiene derecho a presentar una
          reclamación ante la Agencia Española de Protección de Datos (
          <a href="https://www.aepd.es" target="_blank" rel="noopener noreferrer">
            www.aepd.es
          </a>
          ).
        </p>

        <h2 id="cookies">Cookies y tecnologías similares</h2>
        <p>
          El Sitio utiliza almacenamiento local del navegador para recordar su decisión sobre cookies y analítica
          (clave técnica <code>espana_grafico_consent_v1</code>). Esta información se emplea para respetar su elección y no
          constituye un perfil comercial.
        </p>
        <p>
          Las <strong>cookies estrictamente necesarias</strong> permiten el funcionamiento básico del Sitio (por ejemplo,
          preferencias de sesión del propio front). Las <strong>herramientas de analítica</strong> solo se cargan si
          selecciona «Aceptar y continuar» en el banner y si el Titular ha configurado un proveedor en el entorno de
          despliegue. Puede revocar su consentimiento eliminando los datos de sitio para este dominio en la
          configuración de su navegador.
        </p>
        <ul>
          <li>
            <strong>Plausible Analytics:</strong> medición agregada con enfoque orientado a la privacidad. Consulte la
            documentación del proveedor en{" "}
            <a href="https://plausible.io/privacy" target="_blank" rel="noopener noreferrer">
              plausible.io/privacy
            </a>
            .
          </li>
          <li>
            <strong>Google Analytics 4:</strong> si está habilitado, Google actuará como encargado o co-responsable
            según la configuración contractual aplicable. Consulte la información de Google para titulares de sitios.
          </li>
        </ul>

        <h2>Menores de edad</h2>
        <p>
          El Sitio no está dirigido a menores de catorce años. Si tiene conocimiento de que un menor nos ha facilitado
          datos personales, rogamos nos lo comunique para proceder a su supresión.
        </p>

        <h2>Actualización</h2>
        <p>
          Esta política puede actualizarse para reflejar cambios normativos o en los tratamientos. La versión vigente
          será la publicada en esta URL con su fecha de revisión lógica (contenido actualizado en el código fuente del
          Sitio).
        </p>
      </Prose>
    </article>
  );
}
