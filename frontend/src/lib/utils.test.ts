import { describe, expect, it } from "vitest";
import { cn } from "./utils";

describe("cn", () => {
  it("merges plain class strings", () => {
    expect(cn("px-2", "py-4")).toBe("px-2 py-4");
  });

  it("resolves conflicting Tailwind classes, keeping the last one", () => {
    // This is the entire point of using tailwind-merge over a plain
    // clsx/classnames call - "px-2 px-4" would otherwise emit both
    // classes and let CSS cascade order decide, which is fragile.
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("drops falsy values", () => {
    expect(cn("a", false && "b", null, undefined, "c")).toBe("a c");
  });

  it("applies conditional classes from an object", () => {
    expect(cn("base", { active: true, disabled: false })).toBe("base active");
  });
});
