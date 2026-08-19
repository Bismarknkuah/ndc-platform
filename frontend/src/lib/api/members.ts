import { apiClient } from "./client";
import type { PaginatedResponse, User } from "./types";

export interface MemberListParams {
  search?: string;
  organizational_unit_id?: string;
  role_id?: string;
  is_active?: boolean;
  page?: number;
}

export async function listMembers(
  params?: MemberListParams,
): Promise<PaginatedResponse<User>> {
  const { data } = await apiClient.get<PaginatedResponse<User>>("/auth/members/list/", {
    params,
  });
  return data;
}

export async function getMember(id: string): Promise<User> {
  const { data } = await apiClient.get<User>(`/auth/members/${id}/`);
  return data;
}

export async function updateMember(
  id: string,
  payload: {
    is_active?: boolean;
    deactivation_reason?: string;
    first_name?: string;
    last_name?: string;
    national_id_number?: string;
    voter_id_number?: string;
  },
): Promise<User> {
  const { data } = await apiClient.patch<User>(`/auth/members/${id}/`, payload);
  return data;
}

export async function transferMember(
  id: string,
  targetOrganizationalUnitId: string,
  reason?: string,
): Promise<User> {
  const { data } = await apiClient.post<User>(`/auth/members/${id}/transfer/`, {
    target_organizational_unit_id: targetOrganizationalUnitId,
    reason,
  });
  return data;
}
