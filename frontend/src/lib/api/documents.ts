import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const DOCUMENT_CATEGORY_CHOICES = [
  "CONSTITUTION",
  "MINUTES",
  "FORM",
  "POLICY",
  "FINANCIAL_REPORT",
  "MANIFESTO",
  "OTHER",
] as const;

export interface PartyDocumentListItem {
  id: string;
  title: string;
  description: string;
  category: (typeof DOCUMENT_CATEGORY_CHOICES)[number];
  organizational_unit: OrganizationalUnitSummary;
  uploaded_by: UserSummary;
  file_name: string;
  mime_type: string;
  is_public_within_party: boolean;
  is_active: boolean;
  created_at: string;
}

export interface PartyDocument extends PartyDocumentListItem {
  file_base64: string;
}

export async function listDocuments(params?: {
  category?: string;
  organizational_unit_id?: string;
  page?: number;
}): Promise<PaginatedResponse<PartyDocumentListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<PartyDocumentListItem>>(
    "/documents/",
    { params },
  );
  return data;
}

export async function getDocument(id: string): Promise<PartyDocument> {
  const { data } = await apiClient.get<PartyDocument>(`/documents/${id}/`);
  return data;
}

export async function uploadDocument(payload: {
  title: string;
  description?: string;
  category: string;
  organizational_unit_id: string;
  file_base64: string;
  file_name: string;
  mime_type: string;
  is_public_within_party?: boolean;
}): Promise<PartyDocument> {
  const { data } = await apiClient.post<PartyDocument>("/documents/", payload);
  return data;
}

export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`/documents/${id}/`);
}
