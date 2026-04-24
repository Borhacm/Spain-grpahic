export type LegalEntityInfo = {
  legalName: string;
  taxId: string;
  address: string;
  email: string;
  dpoEmail?: string;
};

/**
 * Datos identificativos del responsable (RGPD / LSSI).
 * Definir en despliegue vía variables `NEXT_PUBLIC_*` (ver `.env.example`).
 */
export function parseLegalEntity(): LegalEntityInfo | null {
  const legalName = process.env.NEXT_PUBLIC_LEGAL_ENTITY_NAME?.trim();
  const taxId = process.env.NEXT_PUBLIC_LEGAL_ENTITY_TAX_ID?.trim();
  const address = process.env.NEXT_PUBLIC_LEGAL_ENTITY_ADDRESS?.trim();
  const email = process.env.NEXT_PUBLIC_CONTACT_EMAIL?.trim();
  if (!legalName || !taxId || !address || !email) {
    return null;
  }
  const dpo = process.env.NEXT_PUBLIC_CONTACT_DPO_EMAIL?.trim();
  return {
    legalName,
    taxId,
    address,
    email,
    dpoEmail: dpo || undefined
  };
}
