import { describe, expect, it, beforeEach } from "vitest";
import { useAuthStore } from "./auth-store";
import type { User } from "@/lib/api/types";

function makeUser(): User {
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
  };
}

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      status: "unknown",
    });
  });

  it("starts in the unknown status until a session is restored or cleared", () => {
    expect(useAuthStore.getState().status).toBe("unknown");
  });

  it("setSession populates user and both tokens, and marks authenticated", () => {
    const user = makeUser();
    useAuthStore.getState().setSession(user, "access-1", "refresh-1");

    const state = useAuthStore.getState();
    expect(state.user).toEqual(user);
    expect(state.accessToken).toBe("access-1");
    expect(state.refreshToken).toBe("refresh-1");
    expect(state.status).toBe("authenticated");
  });

  it("setTokens replaces both tokens without touching user or status - the rotating-refresh-token path", () => {
    const user = makeUser();
    useAuthStore.getState().setSession(user, "access-1", "refresh-1");
    useAuthStore.getState().setTokens("access-2", "refresh-2");

    const state = useAuthStore.getState();
    // Both must update together: the backend issues a new refresh token
    // on every refresh call and invalidates the old one, so persisting
    // only the new access token would strand the user after one refresh.
    expect(state.accessToken).toBe("access-2");
    expect(state.refreshToken).toBe("refresh-2");
    expect(state.user).toEqual(user);
    expect(state.status).toBe("authenticated");
  });

  it("clearSession wipes user and tokens and marks unauthenticated", () => {
    useAuthStore.getState().setSession(makeUser(), "access-1", "refresh-1");
    useAuthStore.getState().clearSession();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.status).toBe("unauthenticated");
  });

  it("setUser updates only the user, leaving tokens and status alone", () => {
    useAuthStore.getState().setSession(makeUser(), "access-1", "refresh-1");
    const updated = { ...makeUser(), first_name: "Updated" };
    useAuthStore.getState().setUser(updated);

    const state = useAuthStore.getState();
    expect(state.user?.first_name).toBe("Updated");
    expect(state.accessToken).toBe("access-1");
    expect(state.status).toBe("authenticated");
  });
});
