import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ViewMode = "executive" | "member";

interface ViewModeState {
  /**
   * A purely presentational toggle, not a security boundary: someone
   * holding an executive role always still holds the exact same real
   * permissions on the backend regardless of which view they're
   * looking at here. What this actually does is let an executive
   * switch to seeing their own personal membership portal (dues,
   * their own complaints/welfare requests, their own profile) instead
   * of the executive-focused dashboard, without signing out - and it
   * means removing someone from office never "loses" their membership
   * portal, since that portal was never tied to the office in the
   * first place, just to a view toggle over the same account.
   */
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}

export const useViewModeStore = create<ViewModeState>()(
  persist(
    (set) => ({
      viewMode: "executive",
      setViewMode: (mode) => set({ viewMode: mode }),
    }),
    {
      name: "ndc-view-mode",
    },
  ),
);
