import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const COMPLAINT_TYPE_CHOICES = ["COMPLAINT", "PETITION"] as const;
export const COMPLAINT_STATUS_CHOICES = [
  "SUBMITTED",
  "UNDER_REVIEW",
  "RESOLVED",
  "DISMISSED",
] as const;

export interface Complaint {
  id: string;
  complaint_type: (typeof COMPLAINT_TYPE_CHOICES)[number];
  subject: string;
  description: string;
  submitted_by: UserSummary;
  submitting_unit: OrganizationalUnitSummary;
  target_unit: OrganizationalUnitSummary;
  status: (typeof COMPLAINT_STATUS_CHOICES)[number];
  assigned_to: UserSummary | null;
  resolved_by: UserSummary | null;
  resolved_at: string | null;
  resolution_notes: string;
  created_at: string;
}

export async function listComplaints(params?: {
  complaint_type?: string;
  status?: string;
  target_unit_id?: string;
  page?: number;
}): Promise<PaginatedResponse<Complaint>> {
  const { data } = await apiClient.get<PaginatedResponse<Complaint>>("/complaints/", {
    params,
  });
  return data;
}

export async function createComplaint(payload: {
  complaint_type: string;
  subject: string;
  description: string;
  target_unit_id: string;
}): Promise<Complaint> {
  const { data } = await apiClient.post<Complaint>("/complaints/", payload);
  return data;
}

export async function updateComplaint(
  id: string,
  payload: {
    assigned_to_id?: string;
    status?: "UNDER_REVIEW" | "RESOLVED" | "DISMISSED";
    resolution_notes?: string;
  },
): Promise<Complaint> {
  const { data } = await apiClient.patch<Complaint>(`/complaints/${id}/`, payload);
  return data;
}

export async function supportPetition(
  id: string,
): Promise<{ id: string; supporter_count: number; already_signed: boolean }> {
  const { data } = await apiClient.post(`/complaints/${id}/support/`);
  return data;
}
