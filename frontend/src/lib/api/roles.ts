import { apiClient } from "./client";
import type { RoleSummary } from "./types";

export async function listRoles(params?: { scope?: string; is_active?: boolean }): Promise<RoleSummary[]> {
  const { data } = await apiClient.get<RoleSummary[]>("/auth/roles/", { params });
  return data;
}

export interface CreateRolePayload {
  name: string;
  code: string;
  scope: string;
  is_executive?: boolean;
  permissions?: string[];
  reports_to_id?: string | null;
  dashboard_config?: Record<string, unknown>;
}

export async function createRole(payload: CreateRolePayload): Promise<RoleSummary> {
  const { data } = await apiClient.post<RoleSummary>("/auth/roles/", payload);
  return data;
}

export async function updateRole(
  id: string,
  payload: Partial<CreateRolePayload> & { is_active?: boolean },
): Promise<RoleSummary> {
  const { data } = await apiClient.patch<RoleSummary>(`/auth/roles/${id}/`, payload);
  return data;
}

export async function retireRole(id: string): Promise<void> {
  await apiClient.delete(`/auth/roles/${id}/`);
}
