import type { Metadata } from "next";

import { LegalEntityBlock } from "@/components/legal-entity-block";
import { Prose } from "@/components/ui/prose";
import { parseLegalEntity } from "@/lib/legal-config";
import { SITE_NAME } from "@/lib/site";

const DESCRIPTION = `Condiciones generales de uso del sitio web ${SITE_NAME} (LSSI-CE y normativa aplicable).`;

export const metadata: Metadata = {
  title: "Aviso legal",
  description: DESCRIPTION,
  alternates: { canonical: "/legal/aviso-legal" },
  openGraph: {
    title: `Aviso legal · ${SITE_NAME}`,
    description: DESCRIPTION,
    url: "/legal/aviso-legal"
  }
};

export default function AvisoLegalPage() {
  const entity = parseLegalEntity();

  return (
    <article className="card">
      <h1>Aviso legal</h1>
      <LegalEntityBlock entity={entity} />
      <Prose as="div" className="legal-doc">
        <h2>Objeto y ámbito</h2>
        <p>
          El presente aviso legal regula el acceso y la utilización del sitio web accesible en la dirección URL desde
          la que usted consulta este documento (en adelante, el <strong>Sitio</strong>), titularidad del{" "}
          <strong>Titular</strong> identificado en el apartado anterior. La navegación y el uso del Sitio implican la
          condición de usuario y la aceptación de las presentes condiciones. Si no está de acuerdo, absténgase de
          utilizar el Sitio.
        </p>
        <p>
          El Titular se reserva la facultad de modificar en cualquier momento la presentación, configuración y
          contenidos del Sitio, así como el presente aviso legal, sin perjuicio de su publicación con antelación razonable
          cuando las modificaciones sean sustanciales.
        </p>

        <h2>Condiciones de acceso y uso</h2>
        <p>
          El acceso al Sitio tiene carácter gratuito salvo en los supuestos en que se indique expresamente lo contrario
          para un servicio concreto. El usuario se compromete a utilizar el Sitio de conformidad con la ley, la buena
          fe, el orden público y las presentes condiciones, absteniéndose de realizar actividades que puedan dañar el
          normal funcionamiento del Sitio o los derechos de terceros.
        </p>
        <p>
          Queda prohibido el uso del Sitio con fines ilícitos, lesivos de derechos e intereses del Titular o de
          terceros, o que de cualquier forma dañen, inutilicen, sobrecarguen o deterioren el Sitio o impidan su normal
          utilización por otros usuarios.
        </p>

        <h2>Propiedad intelectual e industrial</h2>
        <p>
          Los textos, diseños, logotipos, estructura de navegación, bases de datos, código y demás contenidos propios
          del Sitio están protegidos por la normativa de propiedad intelectual e industrial. Queda prohibida su
          reproducción, distribución, comunicación pública y transformación, salvo autorización expresa del Titular o
          titular de los derechos correspondientes.
        </p>
        <p>
          Las marcas, nombres comerciales o signos distintivos de terceros que pudieran aparecer en el Sitio son
          propiedad de sus respectivos titulares, sin que su mención implique vinculación o respaldo.
        </p>

        <h2>Exclusión de garantías y responsabilidad</h2>
        <p>
          Los contenidos del Sitio, incluidas las historias de datos, gráficos y metadatos editoriales, se ofrecen con
          fines informativos y divulgativos. El Titular adopta medidas razonables para mantener la información
          actualizada y coherente con las fuentes indicadas, pero no garantiza la exactitud, integridad o vigencia
          absoluta de los datos en todo momento.
        </p>
        <p>
          En la medida permitida por la ley, el Titular no será responsable de los daños y perjuicios de cualquier
          naturaleza derivados del uso del Sitio o de la confianza depositada en sus contenidos, incluidos los
          producidos por virus informáticos, caídas del servicio o enlaces a sitios de terceros.
        </p>

        <h2>Enlaces a sitios de terceros</h2>
        <p>
          El Sitio puede incluir enlaces a páginas web de terceros. El Titular no controla ni asume responsabilidad
          sobre el contenido, políticas de privacidad o prácticas de dichos sitios. La inclusión de un enlace no
          implica necesidad de autorización previa del destino ni constitución de sociedad, colaboración o afiliación.
        </p>

        <h2>Legislación aplicable y jurisdicción</h2>
        <p>
          Las presentes condiciones se rigen por la legislación española. Salvo norma imperativa en contrario, para la
          resolución de controversias serán competentes los juzgados y tribunales del domicilio del usuario consumidor o,
          en su defecto, los del domicilio del Titular en España.
        </p>
      </Prose>
    </article>
  );
}
