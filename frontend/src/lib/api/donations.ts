import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const CAMPAIGN_STATUS_CHOICES = ["PLANNING", "ACTIVE", "COMPLETED", "CANCELLED"] as const;
export const PLEDGE_STATUS_CHOICES = [
  "PLEDGED",
  "PARTIALLY_FULFILLED",
  "FULFILLED",
  "CANCELLED",
] as const;

export interface FundraisingCampaign {
  id: string;
  title: string;
  description: string;
  target_unit: OrganizationalUnitSummary;
  organized_by: UserSummary;
  goal_amount: string;
  currency: string;
  status: (typeof CAMPAIGN_STATUS_CHOICES)[number];
  start_date: string;
  end_date: string;
  created_at: string;
}

export async function listCampaigns(params?: {
  target_unit_id?: string;
  status?: string;
  page?: number;
}): Promise<PaginatedResponse<FundraisingCampaign>> {
  const { data } = await apiClient.get<PaginatedResponse<FundraisingCampaign>>(
    "/donations/campaigns/",
    { params },
  );
  return data;
}

export async function createCampaign(payload: {
  title: string;
  description?: string;
  target_unit_id: string;
  goal_amount: string;
  start_date: string;
  end_date: string;
}): Promise<FundraisingCampaign> {
  const { data } = await apiClient.post<FundraisingCampaign>(
    "/donations/campaigns/",
    payload,
  );
  return data;
}

export async function updateCampaignStatus(
  id: string,
  status: "ACTIVE" | "COMPLETED" | "CANCELLED",
): Promise<FundraisingCampaign> {
  const { data } = await apiClient.patch<FundraisingCampaign>(
    `/donations/campaigns/${id}/`,
    { status },
  );
  return data;
}

export interface CampaignProgress {
  campaign_id: string;
  goal_amount: string;
  total_pledged: string;
  total_fulfilled: string;
  pledge_count: number;
  percentage_of_goal_fulfilled: number;
}

export async function getCampaignProgress(id: string): Promise<CampaignProgress> {
  const { data } = await apiClient.get<CampaignProgress>(
    `/donations/campaigns/${id}/progress/`,
  );
  return data;
}

export interface Pledge {
  id: string;
  campaign_id: string;
  donor_display_name: string;
  donor_user: UserSummary | null;
  donor_name: string | null;
  donor_contact: string | null;
  pledged_amount: string;
  fulfilled_amount: string;
  status: (typeof PLEDGE_STATUS_CHOICES)[number];
  recorded_by: UserSummary;
  finance_record_ids: string[];
  created_at: string;
}

export async function listPledges(campaignId: string): Promise<PaginatedResponse<Pledge>> {
  const { data } = await apiClient.get<PaginatedResponse<Pledge>>("/donations/pledges/", {
    params: { campaign_id: campaignId },
  });
  return data;
}

export async function recordPledge(payload: {
  campaign_id: string;
  donor_user_id?: string;
  donor_name?: string;
  donor_contact?: string;
  pledged_amount: string;
}): Promise<Pledge> {
  const { data } = await apiClient.post<Pledge>("/donations/pledges/", payload);
  return data;
}

export async function fulfillPledge(id: string, amount: string): Promise<Pledge> {
  const { data } = await apiClient.post<Pledge>(`/donations/pledges/${id}/fulfill/`, {
    amount,
  });
  return data;
}
