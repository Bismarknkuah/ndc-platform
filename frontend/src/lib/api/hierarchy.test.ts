import { describe, expect, it } from "vitest";
import {
  ALL_UNIT_TYPES,
  MAIN_CHAIN,
  TEIN_CHAIN,
  AUXILIARY_TYPES,
  expectedParentType,
  unitTypeLabel,
} from "./hierarchy";

describe("unit type catalog", () => {
  it("has exactly 19 unit types (4 main + 6 TEIN + 9 auxiliary)", () => {
    expect(MAIN_CHAIN).toHaveLength(4);
    expect(TEIN_CHAIN).toHaveLength(6);
    expect(AUXILIARY_TYPES).toHaveLength(9);
    expect(ALL_UNIT_TYPES).toHaveLength(19);
  });

  it("main chain runs National down to Branch in order, matching Article 11 of the constitution exactly", () => {
    expect(MAIN_CHAIN).toEqual(["NATIONAL", "REGIONAL", "CONSTITUENCY", "BRANCH"]);
  });
});

describe("unitTypeLabel", () => {
  it("converts a SCREAMING_SNAKE_CASE constant into a readable label", () => {
    expect(unitTypeLabel("DISTRICT_COORDINATING_COMMITTEE")).toBe(
      "District Coordinating Committee",
    );
    expect(unitTypeLabel("BRANCH")).toBe("Branch");
    expect(unitTypeLabel("TEIN_NATIONAL")).toBe("Tein National");
  });
});

describe("expectedParentType", () => {
  it("returns null for a root-level type (National)", () => {
    expect(expectedParentType("NATIONAL")).toBeNull();
  });

  it("returns the immediately preceding type in the main chain", () => {
    expect(expectedParentType("REGIONAL")).toBe("NATIONAL");
    expect(expectedParentType("BRANCH")).toBe("CONSTITUENCY");
    expect(expectedParentType("CONSTITUENCY")).toBe("REGIONAL");
  });

  it("keeps the TEIN chain separate from the main chain", () => {
    expect(expectedParentType("TEIN_NATIONAL")).toBeNull();
    expect(expectedParentType("TEIN_CAMPUS")).toBe("TEIN_REGIONAL");
    // A TEIN type must never be treated as if it belongs to the main chain.
    expect(expectedParentType("TEIN_REGIONAL")).not.toBe("NATIONAL");
  });

  it("returns null for auxiliary types, which attach flexibly rather than via a fixed chain", () => {
    expect(expectedParentType("WOMENS_WING")).toBeNull();
    expect(expectedParentType("COUNCIL_OF_ELDERS")).toBeNull();
  });

  it("treats District Co-ordinating Committee as auxiliary, not a 5th main-chain level", () => {
    // Real per Article 17 of the constitution, but it has no conference or
    // elected executive of its own and its membership is drawn *from*
    // constituency executives rather than containing them - so it attaches
    // flexibly like the other auxiliary bodies, it isn't a rung in the
    // Branch-to-National authority chain.
    expect(expectedParentType("DISTRICT_COORDINATING_COMMITTEE")).toBeNull();
    expect(AUXILIARY_TYPES).toContain("DISTRICT_COORDINATING_COMMITTEE");
    expect(MAIN_CHAIN).not.toContain("DISTRICT_COORDINATING_COMMITTEE");
  });
});
