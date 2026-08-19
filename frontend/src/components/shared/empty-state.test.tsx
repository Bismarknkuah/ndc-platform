import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Inbox } from "lucide-react";
import { EmptyState } from "./empty-state";

describe("EmptyState", () => {
  it("renders the title", () => {
    render(<EmptyState icon={Inbox} title="No results found" />);
    expect(screen.getByText("No results found")).toBeInTheDocument();
  });

  it("renders an optional description when provided", () => {
    render(
      <EmptyState icon={Inbox} title="No members found" description="Try a different search term." />,
    );
    expect(screen.getByText("Try a different search term.")).toBeInTheDocument();
  });

  it("omits the description paragraph entirely when none is given", () => {
    const { container } = render(<EmptyState icon={Inbox} title="Nothing here" />);
    // Only the title <p> should exist - no empty description paragraph.
    expect(container.querySelectorAll("p")).toHaveLength(1);
  });

  it("renders custom action content when provided", () => {
    render(
      <EmptyState icon={Inbox} title="No campaigns yet" action={<button>Create one</button>} />,
    );
    expect(screen.getByRole("button", { name: "Create one" })).toBeInTheDocument();
  });
});
