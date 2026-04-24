import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CountryOverviewDashboard } from "@/app/components/CountryOverviewDashboard";
import type { CountryOverviewData } from "@/lib/country-overview";

afterEach(() => {
  cleanup();
});

function makeData(overrides?: Partial<CountryOverviewData>): CountryOverviewData {
  return {
    executiveKpis: [
      {
        id: "gdp",
        label: "PIB real",
        value: "2,4%",
        delta: "+0,3 pp",
        trend: [1.6, 1.9, 2.0, 2.2, 2.4],
        updatedAt: "Q4 2025",
        source: "BdE",
        status: "Revisado",
      },
    ],
    executiveNarrative: ["Narrativa de prueba"],
    sections: [
      {
        id: "resumen",
        title: "Resumen país",
        description: "Resumen",
        indicators: [
          {
            id: "resumen-balance",
            label: "Saldo público (% PIB)",
            value: "-3,1%",
            change: "+0,4 pp",
            period: "2025",
            source: "Eurostat",
            status: "Último disponible",
            note: "Nota",
            series: Array.from({ length: 36 }, (_, idx) => ({
              period: String(1990 + idx),
              value: -8 + idx * 0.1,
            })),
          },
        ],
      },
    ],
    ...overrides,
  };
}

describe("CountryOverviewDashboard horizons", () => {
  it("muestra solo 1A en series cortas", () => {
    render(<CountryOverviewDashboard data={makeData()} />);
    fireEvent.click(screen.getAllByRole("button", { name: /PIB real/i })[0]);

    const horizonGroup = screen.getByRole("group", { name: /Horizonte temporal/i });
    expect(within(horizonGroup).getByRole("button", { name: "1A" })).toBeTruthy();
    expect(within(horizonGroup).queryByRole("button", { name: "5A" })).toBeNull();
    expect(within(horizonGroup).queryByRole("button", { name: "15A" })).toBeNull();
    expect(within(horizonGroup).queryByRole("button", { name: "30A" })).toBeNull();
  });

  it("muestra horizontes largos cuando hay cobertura y densidad suficientes", () => {
    render(<CountryOverviewDashboard data={makeData()} />);
    const saldoLabel = screen.getByText(/Saldo público/i);
    const saldoButton = saldoLabel.closest("button");
    expect(saldoButton).toBeTruthy();
    fireEvent.click(saldoButton!);

    const horizonGroup = screen.getByRole("group", { name: /Horizonte temporal/i });
    expect(within(horizonGroup).getByRole("button", { name: "1A" })).toBeTruthy();
  });

  it("oculta 30A si no hay cobertura temporal real de 30 años aunque existan muchos puntos", () => {
    const mediumCoverage = makeData({
      sections: [
        {
          id: "resumen",
          title: "Resumen país",
          description: "Resumen",
          indicators: [
            {
              id: "resumen-balance",
              label: "Saldo público (% PIB)",
              value: "-3,1%",
              change: "+0,4 pp",
              period: "2025",
              source: "Eurostat",
              status: "Último disponible",
              note: "Nota",
              // 20 años (2006-2025) con frecuencia trimestral => muchos puntos, poca cobertura 30A
              series: Array.from({ length: 80 }, (_, idx) => {
                const year = 2006 + Math.floor(idx / 4);
                const quarter = (idx % 4) + 1;
                return { period: `Q${quarter} ${year}`, value: -8 + idx * 0.05 };
              }),
            },
          ],
        },
      ],
    });

    render(<CountryOverviewDashboard data={mediumCoverage} />);
    const saldoLabel = screen.getByText(/Saldo público/i);
    const saldoButton = saldoLabel.closest("button");
    expect(saldoButton).toBeTruthy();
    fireEvent.click(saldoButton!);

    const horizonGroup = screen.getByRole("group", { name: /Horizonte temporal/i });
    expect(within(horizonGroup).getByRole("button", { name: "1A" })).toBeTruthy();
    expect(within(horizonGroup).queryByRole("button", { name: "30A" })).toBeNull();
  });

  it("población en modal: serie en personas se muestra en millones (M), no como 49000000 M", () => {
    const data = makeData({
      executiveKpis: [
        {
          id: "population",
          label: "Población total",
          value: "49,6 M",
          delta: "+0,2% interanual",
          trend: [48_900_000, 49_200_000, 49_600_000],
          updatedAt: "2025",
          source: "INE",
          status: "Revisado",
        },
      ],
      sections: [],
    });
    render(<CountryOverviewDashboard data={data} />);
    fireEvent.click(screen.getAllByRole("button", { name: /Población total/i })[0]);
    const dialog = screen.getByRole("dialog");
    const table = within(dialog).getByRole("table");
    const headers = within(table).getAllByRole("columnheader");
    expect(headers.some((h) => /valor\s*\(\s*m\s*\)/i.test(h.textContent ?? ""))).toBe(true);
    expect(within(table).getByRole("cell", { name: "49,6 M" })).toBeTruthy();
    expect(within(table).queryByText(/49000000/)).toBeNull();
  });

  it("modal respeta la unidad del valor (mil EUR), no la del cambio con % interanual", () => {
    const data = makeData({
      sections: [
        {
          id: "empresa-actividad",
          title: "Empresa y actividad",
          description: "Test",
          indicators: [
            {
              id: "empresa-productivity",
              label: "Productividad por ocupado",
              value: "74,3 mil EUR",
              change: "+1,8% interanual",
              period: "2025",
              source: "Eurostat",
              status: "Provisional",
              note: "Nota",
              series: [
                { period: "2024", value: 73 },
                { period: "2025", value: 74.3 },
              ],
            },
          ],
        },
      ],
    });
    render(<CountryOverviewDashboard data={data} />);
    fireEvent.click(screen.getByRole("button", { name: /Productividad por ocupado/i }));
    expect(screen.getByText("Valor (mil EUR)")).toBeTruthy();
  });
});
