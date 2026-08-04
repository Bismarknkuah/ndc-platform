import { describe, expect, it } from "vitest";
import { canSeeNavItem, hasAnyPermission, hasPermission, isExecutive } from "./permissions";
import type { User } from "./api/types";

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: "u1",
    email: "test@example.com",
    phone_number: "0000000000",
    first_name: "Test",
    last_name: "User",
    full_name: "Test User",
    membership_id: "NDC-0001",
    national_id_number: null,
    voter_id_number: null,
    date_of_birth: null,
    gender: null,
    residential_address: null,
    occupation: null,
    marital_status: null,
    emergency_contact_name: null,
    emergency_contact_phone: null,
    must_change_password: false,
    is_active: true,
    is_superadmin: false,
    date_joined: "2026-01-01T00:00:00Z",
    last_login: null,
    role: null,
    organizational_unit: null,
    has_photo: false,
    ...overrides,
  };
}

describe("hasPermission", () => {
  it("denies a null user", () => {
    expect(hasPermission(null, "hierarchy.manage")).toBe(false);
  });

  it("denies an ordinary member with no role", () => {
    expect(hasPermission(makeUser(), "hierarchy.manage")).toBe(false);
  });

  it("grants access when the user's role carries the exact tag", () => {
    const user = makeUser({
      role: {
        id: "r1",
        name: "National Chairman",
        code: "national_chairman",
        scope: "NATIONAL",
        is_executive: true,
        is_active: true,
        permissions: ["hierarchy.manage", "hierarchy.manage_roles"],
        dashboard_config: {},
        reports_to: null,
      },
    });
    expect(hasPermission(user, "hierarchy.manage")).toBe(true);
    expect(hasPermission(user, "finance.manage")).toBe(false);
  });

  it("superadmin bypasses the permission list entirely", () => {
    // Mirrors the backend's own is_superadmin short-circuit - a
    // superadmin with an empty/no role must still pass every check.
    const user = makeUser({ is_superadmin: true, role: null });
    expect(hasPermission(user, "anything.at.all")).toBe(true);
  });
});

describe("hasAnyPermission", () => {
  it("grants access if the user holds at least one of the listed tags", () => {
    const user = makeUser({
      role: {
        id: "r1",
        name: "Branch Secretary",
        code: "branch_secretary",
        scope: "BRANCH",
        is_executive: true,
        is_active: true,
        permissions: ["membership.register"],
        dashboard_config: {},
        reports_to: null,
      },
    });
    expect(hasAnyPermission(user, ["hierarchy.manage", "membership.register"])).toBe(true);
  });

  it("denies access if none of the listed tags match", () => {
    const user = makeUser();
    expect(hasAnyPermission(user, ["hierarchy.manage", "finance.manage"])).toBe(false);
  });
});

describe("canSeeNavItem", () => {
  it("shows items with no permission requirement to anyone", () => {
    expect(canSeeNavItem(makeUser(), {})).toBe(true);
    expect(canSeeNavItem(null, {})).toBe(true);
  });

  it("respects a single required permission", () => {
    const item = { permission: "hierarchy.manage" };
    expect(canSeeNavItem(makeUser(), item)).toBe(false);
    expect(canSeeNavItem(makeUser({ is_superadmin: true }), item)).toBe(true);
  });

  it("respects OR-logic across anyPermissions - the Members-nav regression from Phase 2", () => {
    // This exact case caught a real bug during the build: Members was
    // gated on hierarchy.manage only, hiding it from Branch executives
    // who actually had API access via membership.register instead.
    const branchSecretary = makeUser({
      role: {
        id: "r1",
        name: "Branch Secretary",
        code: "branch_secretary",
        scope: "BRANCH",
        is_executive: true,
        is_active: true,
        permissions: ["membership.register"],
        dashboard_config: {},
        reports_to: null,
      },
    });
    const item = { anyPermissions: ["hierarchy.manage", "membership.register"] };
    expect(canSeeNavItem(branchSecretary, item)).toBe(true);
  });
});

describe("isExecutive", () => {
  it("is false for a null user or one with no role", () => {
    expect(isExecutive(null)).toBe(false);
    expect(isExecutive(makeUser())).toBe(false);
  });

  it("reflects the role's is_executive flag", () => {
    const user = makeUser({
      role: {
        id: "r1",
        name: "Ordinary Committee Member",
        code: "committee_member",
        scope: "BRANCH",
        is_executive: false,
        is_active: true,
        permissions: [],
        dashboard_config: {},
        reports_to: null,
      },
    });
    expect(isExecutive(user)).toBe(false);
  });
});
