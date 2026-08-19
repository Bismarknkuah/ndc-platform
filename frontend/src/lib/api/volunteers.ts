import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const OPPORTUNITY_STATUS_CHOICES = [
  "OPEN",
  "FILLED",
  "COMPLETED",
  "CANCELLED",
] as const;

export interface VolunteerOpportunity {
  id: string;
  title: string;
  description: string;
  event: { id: string; title: string } | null;
  target_unit: OrganizationalUnitSummary;
  organizer: UserSummary;
  needed_count: number;
  filled_count: number;
  location: string;
  scheduled_start: string;
  scheduled_end: string;
  status: (typeof OPPORTUNITY_STATUS_CHOICES)[number];
  created_at: string;
}

export interface VolunteerSignup {
  id: string;
  volunteer: UserSummary;
  status: "SIGNED_UP" | "CONFIRMED" | "CANCELLED" | "COMPLETED";
  signed_up_at: string;
}

export interface VolunteerProfile {
  user: UserSummary;
  skills: string[];
  availability_notes: string;
  is_active: boolean;
  created_at: string;
}

export async function listOpportunities(params?: {
  target_unit_id?: string;
  status?: string;
  upcoming?: boolean;
  page?: number;
}): Promise<PaginatedResponse<VolunteerOpportunity>> {
  const { data } = await apiClient.get<PaginatedResponse<VolunteerOpportunity>>(
    "/volunteers/opportunities/",
    { params },
  );
  return data;
}

export async function createOpportunity(payload: {
  title: string;
  description?: string;
  target_unit_id: string;
  needed_count: number;
  location?: string;
  scheduled_start: string;
  scheduled_end: string;
}): Promise<VolunteerOpportunity> {
  const { data } = await apiClient.post<VolunteerOpportunity>(
    "/volunteers/opportunities/",
    payload,
  );
  return data;
}

export async function signUp(opportunityId: string): Promise<VolunteerSignup> {
  const { data } = await apiClient.post<VolunteerSignup>(
    `/volunteers/opportunities/${opportunityId}/signup/`,
  );
  return data;
}

export async function listSignups(opportunityId: string): Promise<VolunteerSignup[]> {
  const { data } = await apiClient.get<VolunteerSignup[]>(
    `/volunteers/opportunities/${opportunityId}/signups/`,
  );
  return data;
}

export async function fetchMyProfile(): Promise<VolunteerProfile | null> {
  try {
    const { data } = await apiClient.get<VolunteerProfile>("/volunteers/profile/");
    return data;
  } catch {
    return null;
  }
}

export async function updateMyProfile(payload: {
  skills?: string[];
  availability_notes?: string;
  is_active?: boolean;
}): Promise<VolunteerProfile> {
  const { data } = await apiClient.put<VolunteerProfile>("/volunteers/profile/", payload);
  return data;
}
