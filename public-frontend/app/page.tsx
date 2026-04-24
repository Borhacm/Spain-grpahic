import type { Metadata } from "next";

import { CountryOverviewDashboard } from "@/app/components/CountryOverviewDashboard";
import { JsonLd } from "@/components/json-ld";
import { getCountryOverviewData } from "@/lib/country-overview-api";
import { websiteJsonLd } from "@/lib/jsonld";
import { SITE_NAME } from "@/lib/site";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Ficha país España",
  description: "Panel ejecutivo de indicadores macro y estructurales de España con fuentes verificables.",
  alternates: { canonical: "/" },
  openGraph: {
    title: `Ficha país España · ${SITE_NAME}`,
    description: "Dashboard de seguimiento económico y estructural para España.",
    url: "/"
  }
};

export default async function HomePage() {
  const overview = await getCountryOverviewData();
  return (
    <>
      <JsonLd data={websiteJsonLd()} />
      <CountryOverviewDashboard data={overview} />
    </>
  );
}
