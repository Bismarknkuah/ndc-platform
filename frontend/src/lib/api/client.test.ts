import { describe, expect, it, vi } from "vitest";
import { AxiosError } from "axios";
import { ApiError, toApiError } from "./client";

function makeAxiosError(overrides: Partial<AxiosError> = {}): AxiosError {
  const error = new AxiosError("Request failed");
  Object.assign(error, overrides);
  return error;
}

describe("API_BASE_URL", () => {
  it("never falls back to a hardcoded production URL", async () => {
    // Regression test: this module used to fall back to a specific,
    // real production Railway URL when NEXT_PUBLIC_API_BASE_URL wasn't
    // set, which meant a misconfigured deployment (or anyone building
    // this codebase without setting the env var) would silently
    // connect to the real production backend instead of failing
    // obviously. A missing env var must now fail loudly (a failed
    // request to localhost) rather than succeed silently against
    // someone's real data.
    vi.resetModules();
    const original = process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_API_BASE_URL;

    const { API_BASE_URL } = await import("./client");

    expect(API_BASE_URL).not.toMatch(/railway\.app/);
    expect(API_BASE_URL).toMatch(/localhost/);

    if (original !== undefined) process.env.NEXT_PUBLIC_API_BASE_URL = original;
  });
});

describe("ApiError", () => {
  it("carries code, status, and details alongside the message", () => {
    const error = new ApiError("Not found", "not_found", 404, { field: "id" });
    expect(error.message).toBe("Not found");
    expect(error.code).toBe("not_found");
    expect(error.status).toBe(404);
    expect(error.details).toEqual({ field: "id" });
    expect(error.name).toBe("ApiError");
    expect(error).toBeInstanceOf(Error);
  });
});

describe("toApiError", () => {
  it("prefers the backend's structured error envelope when present", () => {
    // Matches the real backend shape confirmed from apps/core/exceptions.py:
    // {"error": {"code", "message", "details"}}
    const axiosError = makeAxiosError({
      response: {
        status: 403,
        data: {
          error: {
            code: "forbidden",
            message: "You do not have authority over this jurisdiction.",
            details: { required_permission: "hierarchy.manage" },
          },
        },
      } as never,
    });

    const result = toApiError(axiosError);
    expect(result.message).toBe("You do not have authority over this jurisdiction.");
    expect(result.code).toBe("forbidden");
    expect(result.status).toBe(403);
    expect(result.details).toEqual({ required_permission: "hierarchy.manage" });
  });

  it("gives a friendly message for a network error with no response at all", () => {
    const axiosError = makeAxiosError({ code: "ERR_NETWORK" });
    const result = toApiError(axiosError);
    expect(result.code).toBe("network_error");
    expect(result.message).toMatch(/can't reach the server/i);
  });

  it("falls back to the raw Axios message when the response has no error envelope", () => {
    const axiosError = makeAxiosError({
      message: "Request failed with status code 500",
      response: { status: 500, data: {} } as never,
    });
    const result = toApiError(axiosError);
    expect(result.code).toBe("unknown_error");
    expect(result.status).toBe(500);
    expect(result.message).toBe("Request failed with status code 500");
  });
});
