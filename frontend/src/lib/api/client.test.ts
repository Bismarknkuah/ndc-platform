import { describe, expect, it } from "vitest";
import { AxiosError } from "axios";
import { ApiError, toApiError } from "./client";

function makeAxiosError(overrides: Partial<AxiosError> = {}): AxiosError {
  const error = new AxiosError("Request failed");
  Object.assign(error, overrides);
  return error;
}

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
