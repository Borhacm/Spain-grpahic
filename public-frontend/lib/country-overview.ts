export type DataSource = "BdE" | "INE" | "Eurostat" | "OECD" | "FMI";
export type DataStatus = "Último disponible" | "Provisional" | "Revisado" | "Desactualizado";

export type SeriesPoint = {
  period: string;
  value: number;
};

export type KpiMetric = {
  id: string;
  label: string;
  value: string;
  delta: string;
  trend: number[];
  updatedAt: string;
  source: DataSource;
  status: DataStatus;
};

export type CountryIndicator = {
  id: string;
  label: string;
  value: string;
  change: string;
  period: string;
  series: SeriesPoint[];
  source: DataSource;
  status: DataStatus;
  note: string;
};

export type CountrySection = {
  id: string;
  title: string;
  description: string;
  indicators: CountryIndicator[];
};

export type CountryOverviewData = {
  executiveKpis: KpiMetric[];
  executiveNarrative: string[];
  sections: CountrySection[];
};

export const periodPresets = ["Actual", "1A", "5A", "10A"] as const;
export type PeriodPreset = (typeof periodPresets)[number];

export const executiveNarrative: string[] = [
  "La economía mantiene crecimiento moderado y una inflación más contenida que en 2023.",
  "El desempleo sigue bajando, aunque permanece en niveles altos frente a otras economías europeas.",
  "La presión demográfica por mayor población y hogares sostiene la demanda de vivienda."
];

export const executiveKpis: KpiMetric[] = [
  {
    id: "gdp",
    label: "PIB real",
    value: "+2,4% interanual",
    delta: "+0,3 pp trimestral",
    trend: [1.6, 1.9, 2, 2.2, 2.4],
    updatedAt: "Q4 2025",
    source: "BdE",
    status: "Revisado"
  },
  {
    id: "inflation",
    label: "Inflación (IPC)",
    value: "2,8%",
    delta: "-0,4 pp interanual",
    trend: [3.6, 3.4, 3.2, 3, 2.8],
    updatedAt: "Mar 2026",
    source: "INE",
    status: "Último disponible"
  },
  {
    id: "unemployment",
    label: "Tasa de paro",
    value: "11,5%",
    delta: "-0,7 pp interanual",
    trend: [12.5, 12.2, 12, 11.8, 11.5],
    updatedAt: "Q1 2026",
    source: "INE",
    status: "Último disponible"
  },
  {
    id: "population",
    label: "Población total",
    value: "49,2 M",
    delta: "+1,1% interanual",
    trend: [48.1, 48.4, 48.6, 48.9, 49.2],
    updatedAt: "2025",
    source: "INE",
    status: "Revisado"
  },
  {
    id: "debt",
    label: "Deuda pública",
    value: "104,3% PIB",
    delta: "-1,2 pp interanual",
    trend: [111.6, 109.8, 108.2, 106.1, 104.3],
    updatedAt: "Q4 2025",
    source: "BdE",
    status: "Provisional"
  },
  {
    id: "public-balance",
    label: "Saldo público",
    value: "-3,1% PIB",
    delta: "+0,4 pp interanual",
    trend: [-8.4, -6.9, -4.7, -3.5, -3.1],
    updatedAt: "2025",
    source: "Eurostat",
    status: "Último disponible"
  },
  {
    id: "housing",
    label: "Compraventas vivienda",
    value: "636 mil",
    delta: "+4,2% interanual",
    trend: [564, 585, 602, 614, 636],
    updatedAt: "2025",
    source: "INE",
    status: "Revisado"
  },
  {
    id: "companies",
    label: "Empresas activas",
    value: "3,45 M",
    delta: "+0,9% interanual",
    trend: [3.31, 3.34, 3.38, 3.42, 3.45],
    updatedAt: "2025",
    source: "INE",
    status: "Último disponible"
  },
  {
    id: "wages",
    label: "Coste laboral medio",
    value: "3.062 EUR/mes",
    delta: "+3,7% interanual",
    trend: [2790, 2860, 2935, 3008, 3062],
    updatedAt: "Q4 2025",
    source: "INE",
    status: "Provisional"
  }
];

export const countrySections: CountrySection[] = [
  {
    id: "resumen",
    title: "Resumen país",
    description: "Panorama macro de crecimiento, precios, empleo y posición fiscal.",
    indicators: [
      {
        id: "resumen-gdp",
        label: "PIB real",
        value: "+2,4%",
        change: "+0,3 pp trimestral",
        period: "Q4 2025",
        source: "BdE",
        status: "Revisado",
        note: "Avance por encima de la media prevista para la eurozona.",
        series: [
          { period: "2021", value: 5.5 },
          { period: "2022", value: 5.8 },
          { period: "2023", value: 2.7 },
          { period: "2024", value: 2.2 },
          { period: "2025", value: 2.4 }
        ]
      },
      {
        id: "resumen-inflation",
        label: "Inflación (IPC)",
        value: "2,8%",
        change: "-0,4 pp interanual",
        period: "Mar 2026",
        source: "INE",
        status: "Último disponible",
        note: "La desinflación gana tracción con menor presión energética.",
        series: [
          { period: "2022", value: 8.4 },
          { period: "2023", value: 3.5 },
          { period: "2024", value: 3.2 },
          { period: "2025", value: 3 },
          { period: "2026", value: 2.8 }
        ]
      },
      {
        id: "resumen-balance",
        label: "Saldo público (% PIB)",
        value: "-3,1%",
        change: "+0,4 pp interanual",
        period: "2025",
        source: "Eurostat",
        status: "Último disponible",
        note: "El déficit se reduce gradualmente, aunque sigue en terreno negativo.",
        series: [
          { period: "2021", value: -8.4 },
          { period: "2022", value: -6.9 },
          { period: "2023", value: -4.7 },
          { period: "2024", value: -3.5 },
          { period: "2025", value: -3.1 }
        ]
      },
      {
        id: "resumen-debt",
        label: "Deuda pública (% PIB)",
        value: "104,3%",
        change: "-1,2 pp interanual",
        period: "Q4 2025",
        source: "BdE",
        status: "Provisional",
        note: "Continúa la reducción gradual, pero en cotas elevadas.",
        series: [
          { period: "2021", value: 118.3 },
          { period: "2022", value: 111.6 },
          { period: "2023", value: 109.8 },
          { period: "2024", value: 106.1 },
          { period: "2025", value: 104.3 }
        ]
      }
    ]
  },
  {
    id: "laboral",
    title: "Mercado laboral",
    description: "Evolución del empleo, desempleo, costes laborales y vacantes.",
    indicators: [
      {
        id: "laboral-employment",
        label: "Ocupación",
        value: "21,9 M",
        change: "+2,0% interanual",
        period: "Q1 2026",
        source: "INE",
        status: "Último disponible",
        note: "Máximos de ocupación, con servicios liderando la creación neta.",
        series: [
          { period: "2021", value: 20.2 },
          { period: "2022", value: 20.5 },
          { period: "2023", value: 20.9 },
          { period: "2024", value: 21.4 },
          { period: "2025", value: 21.9 }
        ]
      },
      {
        id: "laboral-vacancies",
        label: "Vacantes",
        value: "154 mil",
        change: "+6,1% interanual",
        period: "Q4 2025",
        source: "Eurostat",
        status: "Provisional",
        note: "Suben en ramas técnicas y en actividades sanitarias.",
        series: [
          { period: "2021", value: 112 },
          { period: "2022", value: 127 },
          { period: "2023", value: 138 },
          { period: "2024", value: 145 },
          { period: "2025", value: 154 }
        ]
      },
      {
        id: "laboral-activity-rate",
        label: "Tasa de actividad",
        value: "58,9%",
        change: "+0,3 pp interanual",
        period: "Q3 2023",
        source: "INE",
        status: "Último disponible",
        note: "Mide la participación de la población activa y ayuda a interpretar el paro.",
        series: [
          { period: "2021", value: 58.1 },
          { period: "2022", value: 58.4 },
          { period: "2023", value: 58.9 }
        ]
      },
      {
        id: "laboral-unemployment-harmonized",
        label: "Paro armonizado (FMI)",
        value: "10,8%",
        change: "-0,4 pp interanual",
        period: "2026",
        source: "FMI",
        status: "Último disponible",
        note: "Referencia internacional armonizada para comparar España con otras economías.",
        series: [
          { period: "2022", value: 12.9 },
          { period: "2023", value: 12.2 },
          { period: "2024", value: 11.6 },
          { period: "2025", value: 11.2 },
          { period: "2026", value: 10.8 }
        ]
      }
    ]
  },
  {
    id: "digitalizacion-empleo",
    title: "Digitalización y empleo digital",
    description: "Adopción digital empresarial y disponibilidad de talento TIC en el mercado laboral.",
    indicators: [
      {
        id: "digital-ict-specialists",
        label: "Especialistas TIC sobre empleo total",
        value: "4,8%",
        change: "+0,2 pp interanual",
        period: "2025",
        source: "Eurostat",
        status: "Último disponible",
        note: "El peso del empleo tecnológico crece, aunque persiste brecha de talento en perfiles avanzados.",
        series: [
          { period: "2021", value: 4.1 },
          { period: "2022", value: 4.2 },
          { period: "2023", value: 4.4 },
          { period: "2024", value: 4.6 },
          { period: "2025", value: 4.8 }
        ]
      },
      {
        id: "digital-firms-basic-intensity",
        label: "Empresas con intensidad digital básica",
        value: "68%",
        change: "+3,0 pp interanual",
        period: "2025",
        source: "Eurostat",
        status: "Último disponible",
        note: "Aumenta la base digital en pymes, impulsada por cloud y herramientas de colaboración.",
        series: [
          { period: "2021", value: 57 },
          { period: "2022", value: 60 },
          { period: "2023", value: 63 },
          { period: "2024", value: 65 },
          { period: "2025", value: 68 }
        ]
      },
      {
        id: "digital-oecd-dgi",
        label: "OECD Digital Government Index",
        value: "7,4/10",
        change: "+0,3 puntos",
        period: "2025",
        source: "OECD",
        status: "Último disponible",
        note: "Índice comparativo internacional en escala 0-10 (mayor es mejor).",
        series: [
          { period: "2021", value: 6.5 },
          { period: "2022", value: 6.7 },
          { period: "2023", value: 6.9 },
          { period: "2024", value: 7.1 },
          { period: "2025", value: 7.4 }
        ]
      },
      {
        id: "digital-oecd-ourdata",
        label: "OECD OURdata Index",
        value: "8,2/10",
        change: "+0,4 puntos",
        period: "2025",
        source: "OECD",
        status: "Último disponible",
        note: "Índice comparativo internacional en escala 0-10 (mayor es mejor).",
        series: [
          { period: "2021", value: 7.0 },
          { period: "2022", value: 7.3 },
          { period: "2023", value: 7.6 },
          { period: "2024", value: 7.8 },
          { period: "2025", value: 8.2 }
        ]
      }
    ]
  },
  {
    id: "proyecciones-fmi",
    title: "Proyecciones FMI",
    description: "Escenario macro de crecimiento, precios y paro para España.",
    indicators: [
      {
        id: "fmi-gdp-growth",
        label: "FMI PIB real (variación anual)",
        value: "2,5%",
        change: "-0,3 pp interanual",
        period: "2026",
        source: "FMI",
        status: "Último disponible",
        note: "Serie del DataMapper del FMI para comparativa internacional homogénea.",
        series: [
          { period: "2022", value: 5.8 },
          { period: "2023", value: 2.7 },
          { period: "2024", value: 2.5 },
          { period: "2025", value: 2.3 },
          { period: "2026", value: 2.0 }
        ]
      },
      {
        id: "fmi-inflation",
        label: "FMI inflación media",
        value: "2,9%",
        change: "-0,5 pp interanual",
        period: "2026",
        source: "FMI",
        status: "Último disponible",
        note: "Inflación media anual según metodología comparada del FMI.",
        series: [
          { period: "2022", value: 8.3 },
          { period: "2023", value: 3.5 },
          { period: "2024", value: 3.0 },
          { period: "2025", value: 2.9 },
          { period: "2026", value: 2.6 }
        ]
      },
      {
        id: "fmi-unemployment",
        label: "FMI tasa de paro",
        value: "10,8%",
        change: "-0,4 pp interanual",
        period: "2026",
        source: "FMI",
        status: "Último disponible",
        note: "Tasa de desempleo armonizada para comparabilidad entre economías.",
        series: [
          { period: "2022", value: 12.9 },
          { period: "2023", value: 12.2 },
          { period: "2024", value: 11.6 },
          { period: "2025", value: 11.2 },
          { period: "2026", value: 10.8 }
        ]
      }
    ]
  },
  {
    id: "demografia-vivienda",
    title: "Demografía y vivienda",
    description: "Cambio demográfico, hogares y presión sobre el mercado residencial.",
    indicators: [
      {
        id: "demo-population",
        label: "Población total",
        value: "49,2 M",
        change: "+1,1% interanual",
        period: "2025",
        source: "INE",
        status: "Revisado",
        note: "El crecimiento se apoya en migración neta positiva.",
        series: [
          { period: "2021", value: 47.4 },
          { period: "2022", value: 47.8 },
          { period: "2023", value: 48.3 },
          { period: "2024", value: 48.9 },
          { period: "2025", value: 49.2 }
        ]
      },
      {
        id: "demo-households",
        label: "Hogares",
        value: "19,6 M",
        change: "+1,3% interanual",
        period: "2025",
        source: "INE",
        status: "Último disponible",
        note: "Aumenta el número de hogares unipersonales.",
        series: [
          { period: "2021", value: 18.8 },
          { period: "2022", value: 19.1 },
          { period: "2023", value: 19.3 },
          { period: "2024", value: 19.4 },
          { period: "2025", value: 19.6 }
        ]
      },
      {
        id: "demo-household-size",
        label: "Tamaño medio del hogar",
        value: "2,50 personas",
        change: "-0,02 interanual",
        period: "2025",
        source: "INE",
        status: "Último disponible",
        note: "La reducción del tamaño medio refuerza la presión estructural sobre la demanda residencial.",
        series: [
          { period: "2021", value: 2.58 },
          { period: "2022", value: 2.56 },
          { period: "2023", value: 2.54 },
          { period: "2024", value: 2.52 },
          { period: "2025", value: 2.5 }
        ]
      },
      {
        id: "demo-net-migration",
        label: "Saldo migratorio neto",
        value: "+642 mil",
        change: "+7,6% interanual",
        period: "2025",
        source: "INE",
        status: "Provisional",
        note: "El saldo migratorio mantiene el crecimiento poblacional y sostiene la formación de nuevos hogares.",
        series: [
          { period: "2021", value: 311 },
          { period: "2022", value: 398 },
          { period: "2023", value: 512 },
          { period: "2024", value: 597 },
          { period: "2025", value: 642 }
        ]
      }
    ]
  },
  {
    id: "empresa-actividad",
    title: "Empresa y actividad",
    description: "Tejido empresarial, negocio y avance de digitalización productiva.",
    indicators: [
      {
        id: "empresa-total",
        label: "Empresas activas",
        value: "3,45 M",
        change: "+0,9% interanual",
        period: "2025",
        source: "INE",
        status: "Último disponible",
        note: "Las microempresas siguen siendo el grueso del tejido empresarial.",
        series: [
          { period: "2021", value: 3.27 },
          { period: "2022", value: 3.31 },
          { period: "2023", value: 3.34 },
          { period: "2024", value: 3.42 },
          { period: "2025", value: 3.45 }
        ]
      },
      {
        id: "empresa-digital",
        label: "Empresas con venta online",
        value: "31%",
        change: "+2,1 pp interanual",
        period: "2025",
        source: "INE",
        status: "Provisional",
        note: "Se acelera la adopción digital en pymes orientadas a consumo.",
        series: [
          { period: "2021", value: 23.5 },
          { period: "2022", value: 25.1 },
          { period: "2023", value: 27.4 },
          { period: "2024", value: 28.9 },
          { period: "2025", value: 31 }
        ]
      },
      {
        id: "empresa-net-creation",
        label: "Creación neta de empresas",
        value: "58 mil",
        change: "+9,4% interanual",
        period: "2025",
        source: "INE",
        status: "Último disponible",
        note: "La diferencia entre altas y bajas acelera la expansión del tejido empresarial.",
        series: [
          { period: "2021", value: 35 },
          { period: "2022", value: 41 },
          { period: "2023", value: 46 },
          { period: "2024", value: 53 },
          { period: "2025", value: 58 }
        ]
      },
      {
        id: "empresa-productivity",
        label: "Productividad por ocupado",
        value: "74,3 mil EUR",
        change: "+1,8% interanual",
        period: "2025",
        source: "Eurostat",
        status: "Provisional",
        note: "Mejora la eficiencia media, aunque con avances heterogéneos por sector.",
        series: [
          { period: "2021", value: 69.8 },
          { period: "2022", value: 71.1 },
          { period: "2023", value: 72.2 },
          { period: "2024", value: 73.0 },
          { period: "2025", value: 74.3 }
        ]
      }
    ]
  }
];

export function getCountryOverviewSeedData(): CountryOverviewData {
  return {
    executiveKpis: executiveKpis.map((kpi) => ({ ...kpi, trend: [...kpi.trend] })),
    executiveNarrative: [...executiveNarrative],
    sections: countrySections.map((section) => ({
      ...section,
      indicators: section.indicators.map((indicator) => ({
        ...indicator,
        series: indicator.series.map((point) => ({ ...point }))
      }))
    }))
  };
}
