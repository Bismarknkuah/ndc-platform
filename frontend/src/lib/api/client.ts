import axios, {
  type AxiosInstance,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "@/stores/auth-store";
import type { ApiErrorBody } from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "https://ndc-platform-production.up.railway.app/api/v1";

export class ApiError extends Error {
  code: string;
  status: number | undefined;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    code: string,
    status?: number,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export function toApiError(error: AxiosError): ApiError {
  const body = error.response?.data as ApiErrorBody | undefined;

  if (body?.error) {
    return new ApiError(
      body.error.message,
      body.error.code,
      error.response?.status,
      body.error.details,
    );
  }

  if (error.code === "ERR_NETWORK") {
    return new ApiError(
      "Can't reach the server. Check your connection and try again.",
      "network_error",
    );
  }

  return new ApiError(
    error.message || "Something went wrong.",
    "unknown_error",
    error.response?.status,
  );
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;

    if (token) {
      config.headers.set("Authorization", `Bearer ${token}`);
    }

    return config;
  },
);

// Prevent multiple refresh requests at the same time
let refreshPromise: Promise<boolean> | null = null;

async function attemptRefresh(): Promise<boolean> {
  const { refreshToken, setTokens, clearSession } =
    useAuthStore.getState();

  if (!refreshToken) return false;

  try {
    const response = await axios.post(
      `${API_BASE_URL}/auth/refresh/`,
      {
        refresh: refreshToken,
      },
    );

    setTokens(
      response.data.access,
      response.data.refresh,
    );

    return true;
  } catch {
    clearSession();
    return false;
  }
}

apiClient.interceptors.response.use(
  (response) => response,

  async (error: AxiosError) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & {
          _retried?: boolean;
        })
      | undefined;

    const isUnauthorized = error.response?.status === 401;

    const isAuthEndpoint =
      originalRequest?.url?.includes("/auth/login") ||
      originalRequest?.url?.includes("/auth/refresh");

    if (
      isUnauthorized &&
      originalRequest &&
      !originalRequest._retried &&
      !isAuthEndpoint
    ) {
      originalRequest._retried = true;

      refreshPromise ??= attemptRefresh().finally(() => {
        refreshPromise = null;
      });

      const refreshed = await refreshPromise;

      if (refreshed) {
        const token =
          useAuthStore.getState().accessToken;

        if (token) {
          originalRequest.headers.set(
            "Authorization",
            `Bearer ${token}`,
          );
        }

        return apiClient(originalRequest);
      }
    }

    return Promise.reject(toApiError(error));
  },
);