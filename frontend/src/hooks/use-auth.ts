"use client";

import { useCallback, useEffect, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/auth-store";
import * as authApi from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const restoreAttempted = useRef(false);

  const user = useAuthStore((s) => s.user);
  const status = useAuthStore((s) => s.status);
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const setSession = useAuthStore((s) => s.setSession);
  const setUser = useAuthStore((s) => s.setUser);
  const clearSession = useAuthStore((s) => s.clearSession);
  const setStatus = useAuthStore((s) => s.setStatus);

  // On first mount (including after a hard refresh, where Zustand's
  // persist middleware has already rehydrated any stored tokens),
  // verify the access token is still good by asking the backend who we
  // are - catches an expired/blacklisted token before the app shell
  // renders as if logged in.
  useEffect(() => {
    if (restoreAttempted.current) return;
    restoreAttempted.current = true;

    if (!accessToken) {
      setStatus("unauthenticated");
      return;
    }

    authApi
      .fetchMe()
      .then((freshUser) => {
        setUser(freshUser);
        setStatus("authenticated");
      })
      .catch(() => {
        // The response interceptor already tried a refresh-and-retry
        // before this promise rejects, so a failure here means the
        // refresh token is also gone/invalid.
        clearSession();
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (data) => {
      setSession(data.user, data.tokens.access, data.tokens.refresh);
      toast.success(`Welcome back, ${data.user.first_name}.`);
      router.push("/dashboard");
    },
    onError: (error: ApiError) => {
      toast.error(error.message || "Login failed.");
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      if (refreshToken) {
        await authApi.logout(refreshToken).catch(() => {
          // Best-effort server-side revocation - clear local session regardless.
        });
      }
    },
    onSettled: () => {
      clearSession();
      queryClient.clear();
      router.push("/login");
    },
  });

  const doLogout = useCallback(() => logoutMutation.mutate(), [logoutMutation]);

  return {
    user,
    status,
    isAuthenticated: status === "authenticated",
    login: loginMutation.mutate,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error as ApiError | null,
    logout: doLogout,
  };
}
