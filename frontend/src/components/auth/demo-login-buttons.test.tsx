import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DemoLoginButtons, DEMO_ACCOUNTS } from "./demo-login-buttons";

describe("DemoLoginButtons", () => {
  it("renders one button per demo account", () => {
    render(<DemoLoginButtons onSelect={vi.fn()} />);
    for (const account of DEMO_ACCOUNTS) {
      expect(screen.getByRole("button", { name: new RegExp(account.label) })).toBeInTheDocument();
    }
  });

  it("calls onSelect with the matching account when clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<DemoLoginButtons onSelect={onSelect} />);

    await user.click(screen.getByRole("button", { name: /National Chairman/ }));

    expect(onSelect).toHaveBeenCalledOnce();
    expect(onSelect.mock.calls[0][0].email).toBe("demo.national@ndc.example");
  });

  it("disables every button when disabled is true", () => {
    render(<DemoLoginButtons onSelect={vi.fn()} disabled />);
    for (const account of DEMO_ACCOUNTS) {
      expect(screen.getByRole("button", { name: new RegExp(account.label) })).toBeDisabled();
    }
  });
});
