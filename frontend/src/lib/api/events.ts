import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const CAMPAIGN_STATUS_CHOICES = ["PLANNING", "ACTIVE", "COMPLETED", "CANCELLED"] as const;
export const EVENT_TYPE_CHOICES = [
  "RALLY",
  "TOWN_HALL",
  "CAMPAIGN_EVENT",
  "FUNDRAISER",
  "COMMUNITY_OUTREACH",
  "OTHER",
] as const;
export const EVENT_STATUS_CHOICES = ["SCHEDULED", "ONGOING", "COMPLETED", "CANCELLED"] as const;
export const RSVP_STATUS_CHOICES = ["ATTENDING", "DECLINED"] as const;

export interface Campaign {
  id: string;
  title: string;
  description: string;
  goal_description: string;
  target_unit: OrganizationalUnitSummary;
  organized_by: UserSummary;
  status: (typeof CAMPAIGN_STATUS_CHOICES)[number];
  start_date: string;
  end_date: string;
  created_at: string;
}

export async function listEventCampaigns(params?: {
  target_unit_id?: string;
  status?: string;
  page?: number;
}): Promise<PaginatedResponse<Campaign>> {
  const { data } = await apiClient.get<PaginatedResponse<Campaign>>("/events/campaigns/", {
    params,
  });
  return data;
}

export async function createEventCampaign(payload: {
  title: string;
  description?: string;
  goal_description?: string;
  target_unit_id: string;
  start_date: string;
  end_date: string;
}): Promise<Campaign> {
  const { data } = await apiClient.post<Campaign>("/events/campaigns/", payload);
  return data;
}

export interface PartyEvent {
  id: string;
  title: string;
  description: string;
  event_type: (typeof EVENT_TYPE_CHOICES)[number];
  campaign: { id: string; title: string } | null;
  target_unit: OrganizationalUnitSummary;
  organizer: UserSummary;
  location: string;
  scheduled_start: string;
  scheduled_end: string;
  status: (typeof EVENT_STATUS_CHOICES)[number];
  created_at: string;
}

export async function listEvents(params?: {
  target_unit_id?: string;
  campaign_id?: string;
  status?: string;
  upcoming?: boolean;
  page?: number;
}): Promise<PaginatedResponse<PartyEvent>> {
  const { data } = await apiClient.get<PaginatedResponse<PartyEvent>>("/events/", { params });
  return data;
}

export async function createEvent(payload: {
  title: string;
  description?: string;
  event_type: string;
  campaign_id?: string | null;
  target_unit_id: string;
  location?: string;
  scheduled_start: string;
  scheduled_end: string;
}): Promise<PartyEvent> {
  const { data } = await apiClient.post<PartyEvent>("/events/", payload);
  return data;
}

export async function rsvpToEvent(
  eventId: string,
  status: "ATTENDING" | "DECLINED",
): Promise<void> {
  await apiClient.post(`/events/${eventId}/rsvp/`, { status });
}

export async function getEventRsvps(eventId: string): Promise<{
  attending_count: number;
  declined_count: number;
  rsvps: { user: UserSummary; status: string; responded_at: string }[];
}> {
  const { data } = await apiClient.get(`/events/${eventId}/rsvps/`);
  return data;
}
