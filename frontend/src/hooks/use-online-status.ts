"use client";

import { useSyncExternalStore } from "react";

function subscribe(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

/** True/false based on the real navigator.onLine + online/offline
 * browser events, via useSyncExternalStore (the correct primitive for
 * subscribing to external browser state, rather than an effect that
 * calls setState). Server snapshot assumes online, since there's no
 * network state on the server. */
export function useOnlineStatus(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => navigator.onLine,
    () => true,
  );
}
