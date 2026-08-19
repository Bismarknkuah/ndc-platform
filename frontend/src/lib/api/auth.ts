import { apiClient } from "./client";
import type { LoginResponse, TokenPair, User } from "./types";

export async function login(email: string, password: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/auth/login/", { email, password });
  return data;
}

export async function logout(refreshToken: string): Promise<void> {
  await apiClient.post("/auth/logout/", { refresh: refreshToken });
}

export async function fetchMe(): Promise<User> {
  const { data } = await apiClient.get<User>("/auth/me/");
  return data;
}

export async function updateMe(payload: Partial<User>): Promise<User> {
  const { data } = await apiClient.patch<User>("/auth/me/", payload);
  return data;
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await apiClient.post("/auth/change-password/", {
    old_password: oldPassword,
    new_password: newPassword,
  });
}

export async function refreshTokenPair(refreshToken: string): Promise<TokenPair> {
  const { data } = await apiClient.post<TokenPair>("/auth/refresh/", { refresh: refreshToken });
  return data;
}
