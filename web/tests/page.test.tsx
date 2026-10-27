import { render, screen } from "@testing-library/react";
import Home from "@/app/page";
import { NOTICE } from "@/lib/notice";

describe("home page", () => {
  it("shows the name and the engineer validation notice", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "Ersatz" })).toBeDefined();
    expect(screen.getByRole("note").textContent).toBe(NOTICE);
  });
});
