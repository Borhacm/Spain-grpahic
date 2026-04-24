import { describe, expect, it } from "vitest";

import { formatDate } from "@/lib/format-date";

const MONTH_RE =
  /(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)/;

describe("formatDate", () => {
  it("devuelve la cadena original si no es una fecha válida", () => {
    expect(formatDate("")).toBe("");
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });

  it("para una ISO válida produce «día mes año» en español (mes del catálogo)", () => {
    const s = formatDate("2026-04-24T12:00:00.000Z");
    expect(s).toMatch(/^\d{1,2} /);
    expect(s).toMatch(MONTH_RE);
    expect(s).toMatch(/ \d{4}$/);
  });
});
