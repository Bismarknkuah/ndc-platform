import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrgUnitPath } from "./org-unit-path";
import type { OrganizationalUnitSummary } from "@/lib/api/types";

const units: OrganizationalUnitSummary[] = [
  { id: "1", name: "National", code: "NAT", unit_type: "NATIONAL" },
  { id: "2", name: "Ashanti Region", code: "ASH", unit_type: "REGIONAL" },
  { id: "3", name: "Kumasi Central", code: "KUM", unit_type: "CONSTITUENCY" },
];

describe("OrgUnitPath", () => {
  it("renders nothing when given an empty unit list", () => {
    const { container } = render(<OrgUnitPath units={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders every unit's name in order", () => {
    render(<OrgUnitPath units={units} />);
    expect(screen.getByText("National")).toBeInTheDocument();
    expect(screen.getByText("Ashanti Region")).toBeInTheDocument();
    expect(screen.getByText("Kumasi Central")).toBeInTheDocument();
  });

  it("renders the last (current) unit as plain text, not a clickable button", () => {
    render(<OrgUnitPath units={units} onNavigate={vi.fn()} />);
    // Only the two ancestor segments should be interactive buttons -
    // the current/last unit is the destination, not a navigation target.
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });

  it("calls onNavigate with the clicked unit, not the last one", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();
    render(<OrgUnitPath units={units} onNavigate={onNavigate} />);

    await user.click(screen.getByText("Ashanti Region"));
    expect(onNavigate).toHaveBeenCalledWith(units[1]);
  });
});
