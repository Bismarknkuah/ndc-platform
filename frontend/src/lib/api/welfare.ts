import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const WELFARE_CATEGORY_CHOICES = [
  "BEREAVEMENT",
  "MEDICAL",
  "EDUCATIONAL",
  "EMERGENCY",
  "OTHER",
] as const;
export const WELFARE_STATUS_CHOICES = [
  "SUBMITTED",
  "UNDER_REVIEW",
  "APPROVED",
  "REJECTED",
  "DISBURSED",
] as const;

export interface WelfareRequest {
  id: string;
  requester: UserSummary;
  organizational_unit: OrganizationalUnitSummary;
  category: (typeof WELFARE_CATEGORY_CHOICES)[number];
  description: string;
  amount_requested: string;
  supporting_document_base64: string | null;
  status: (typeof WELFARE_STATUS_CHOICES)[number];
  reviewed_by: UserSummary | null;
  reviewed_at: string | null;
  resolution_notes: string;
  finance_record_id: string | null;
  created_at: string;
}

export async function listWelfareRequests(params?: {
  status?: string;
  organizational_unit_id?: string;
  page?: number;
}): Promise<PaginatedResponse<WelfareRequest>> {
  const { data } = await apiClient.get<PaginatedResponse<WelfareRequest>>(
    "/welfare/requests/",
    { params },
  );
  return data;
}

export async function submitWelfareRequest(payload: {
  category: string;
  description: string;
  amount_requested: string;
  supporting_document_base64?: string | null;
}): Promise<WelfareRequest> {
  const { data } = await apiClient.post<WelfareRequest>("/welfare/requests/", payload);
  return data;
}

export async function updateWelfareRequestStatus(
  id: string,
  status: "UNDER_REVIEW" | "APPROVED" | "REJECTED" | "DISBURSED",
  resolutionNotes?: string,
): Promise<WelfareRequest> {
  const { data } = await apiClient.patch<WelfareRequest>(`/welfare/requests/${id}/`, {
    status,
    resolution_notes: resolutionNotes,
  });
  return data;
}
