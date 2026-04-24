import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StoryMeta } from "@/app/components/StoryMeta";

describe("StoryMeta", () => {
  it("no renderiza nada si no hay fecha, tema ni tags", () => {
    const { container } = render(<StoryMeta />);
    expect(container.firstChild).toBeNull();
  });

  it("muestra fecha (time), tema y lista de etiquetas", () => {
    render(
      <StoryMeta
        topic="economy"
        tags={["ipc", "macro"]}
        publishedAt="2026-04-24T12:00:00.000Z"
        layout="hero"
      />
    );

    const time = screen.getByRole("time");
    expect(time.getAttribute("dateTime")).toBe("2026-04-24T12:00:00.000Z");
    expect(time.textContent).toMatch(/\d{4}/);

    expect(screen.getByText("economy")).toBeTruthy();

    const tagList = screen.getByRole("list", { name: /Etiquetas/i });
    expect(within(tagList).getByText("ipc")).toBeTruthy();
    expect(within(tagList).getByText("macro")).toBeTruthy();
  });
});
