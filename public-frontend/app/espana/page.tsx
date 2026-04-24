import type { Metadata } from "next";

import { CountryOverviewDashboard } from "@/app/components/CountryOverviewDashboard";
import { getCountryOverviewData } from "@/lib/country-overview-api";
import { SITE_NAME } from "@/lib/site";

export const metadata: Metadata = {
  title: "Ficha país España",
  description: "Panel ejecutivo de indicadores macro y estructurales de España con fuentes verificables.",
  alternates: { canonical: "/espana" },
  openGraph: {
    title: `Ficha país España · ${SITE_NAME}`,
    description: "Dashboard de seguimiento económico y estructural para España.",
    url: "/espana"
  }
};

export default async function CountryOverviewPage() {
  const overview = await getCountryOverviewData();
  return <CountryOverviewDashboard data={overview} />;
}
