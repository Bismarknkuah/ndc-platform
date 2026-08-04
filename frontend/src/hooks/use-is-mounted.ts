"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/**
 * True only after client-side hydration. Used to defer rendering of
 * anything that depends on browser-only state (resolved theme, viewport,
 * etc.) so server and first client render match. Implemented with
 * useSyncExternalStore rather than an effect + setState, since the
 * server/client snapshots are exactly what that API is for - avoids the
 * "setState synchronously in an effect" anti-pattern.
 */
export function useIsMounted(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
