import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const MEDIA_TYPE_CHOICES = ["PHOTO", "VIDEO", "AUDIO", "PRESS_CLIPPING", "OTHER"] as const;

export interface MediaAssetListItem {
  id: string;
  title: string;
  description: string;
  media_type: (typeof MEDIA_TYPE_CHOICES)[number];
  tags: string[];
  organizational_unit: OrganizationalUnitSummary;
  uploaded_by: UserSummary;
  event: { id: string; title: string } | null;
  external_url: string | null;
  is_public_within_party: boolean;
  is_active: boolean;
  created_at: string;
}

export interface MediaAsset extends MediaAssetListItem {
  file_base64: string | null;
}

export async function listMedia(params?: {
  media_type?: string;
  organizational_unit_id?: string;
  event_id?: string;
  page?: number;
}): Promise<PaginatedResponse<MediaAssetListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<MediaAssetListItem>>("/media/", {
    params,
  });
  return data;
}

export async function getMediaAsset(id: string): Promise<MediaAsset> {
  const { data } = await apiClient.get<MediaAsset>(`/media/${id}/`);
  return data;
}

export async function uploadMedia(payload: {
  title: string;
  description?: string;
  media_type: string;
  tags?: string[];
  organizational_unit_id: string;
  event_id?: string | null;
  file_base64?: string | null;
  external_url?: string | null;
  is_public_within_party?: boolean;
}): Promise<MediaAsset> {
  const { data } = await apiClient.post<MediaAsset>("/media/", payload);
  return data;
}

export async function deleteMediaAsset(id: string): Promise<void> {
  await apiClient.delete(`/media/${id}/`);
}
