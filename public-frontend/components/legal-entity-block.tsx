import type { LegalEntityInfo } from "@/lib/legal-config";
import { SITE_NAME } from "@/lib/site";

type Props = { entity: LegalEntityInfo | null };

export function LegalEntityBlock({ entity }: Props) {
  if (!entity) {
    return (
      <aside className="legal-notice legal-notice--warn" role="note">
        <p>
          <strong>Identificación del titular:</strong> complete en el despliegue las variables de entorno{" "}
          <code>NEXT_PUBLIC_LEGAL_ENTITY_NAME</code>, <code>NEXT_PUBLIC_LEGAL_ENTITY_TAX_ID</code>,{" "}
          <code>NEXT_PUBLIC_LEGAL_ENTITY_ADDRESS</code> y <code>NEXT_PUBLIC_CONTACT_EMAIL</code> (opcional:{" "}
          <code>NEXT_PUBLIC_CONTACT_DPO_EMAIL</code>). Hasta entonces, los apartados siguientes se entienden referidos
          al responsable que eventualmente los publique bajo la marca {SITE_NAME}.
        </p>
      </aside>
    );
  }

  return (
    <aside className="legal-notice" role="region" aria-label="Identificación del titular">
      <dl className="legal-dl">
        <div>
          <dt>Denominación social</dt>
          <dd>{entity.legalName}</dd>
        </div>
        <div>
          <dt>NIF / CIF</dt>
          <dd>{entity.taxId}</dd>
        </div>
        <div>
          <dt>Domicilio</dt>
          <dd>{entity.address}</dd>
        </div>
        <div>
          <dt>Correo de contacto</dt>
          <dd>
            <a href={`mailto:${entity.email}`}>{entity.email}</a>
          </dd>
        </div>
        {entity.dpoEmail ? (
          <div>
            <dt>Delegado de protección de datos</dt>
            <dd>
              <a href={`mailto:${entity.dpoEmail}`}>{entity.dpoEmail}</a>
            </dd>
          </div>
        ) : null}
      </dl>
    </aside>
  );
}
