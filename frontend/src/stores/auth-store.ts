import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/lib/api/types";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  /** "unknown" until restoreSession() resolves - lets the app shell show a
   * splash instead of flashing the login screen on every hard refresh. */
  status: "unknown" | "authenticated" | "unauthenticated";

  setSession: (user: User, accessToken: string, refreshToken: string) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User) => void;
  clearSession: () => void;
  setStatus: (status: AuthState["status"]) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      status: "unknown",

      setSession: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken, status: "authenticated" }),

      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),

      setUser: (user) => set({ user }),

      clearSession: () =>
        set({ user: null, accessToken: null, refreshToken: null, status: "unauthenticated" }),

      setStatus: (status) => set({ status }),
    }),
    {
      name: "ndc-auth",
      // Only persist what's needed to silently restore a session on
      // reload; `status` always starts "unknown" on a fresh load so the
      // app shell re-verifies with the backend rather than trusting
      // stale persisted state.
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    },
  ),
);
