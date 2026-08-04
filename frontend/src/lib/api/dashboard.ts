import { apiClient } from "./client";
import type { OrganizationalUnitSummary, User } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export interface Meeting {
  id: string;
  title: string;
  description: string;
  meeting_type: string;
  department: { id: string; name: string } | null;
  target_unit: OrganizationalUnitSummary;
  host: UserSummary;
  scheduled_start: string;
  scheduled_end: string;
  meeting_url: string;
  status: string;
  created_at: string;
}

export interface Broadcast {
  id: string;
  title: string;
  body: string;
  kind: string;
  priority: string;
  issued_by: UserSummary;
  target_unit: OrganizationalUnitSummary;
  requires_acknowledgement: boolean;
  created_at: string;
}

export interface PendingTask {
  id: string;
  title: string;
  engagement_type: string;
  platform_name: string;
  scheduled_at: string;
  status: string;
}

export interface TeamLed {
  department: { id: string; name: string };
  organizational_unit: { id: string; name: string };
  position: string;
  team_size: number;
  pending_tasks: number;
}

export interface DashboardElection {
  id: string;
  title: string;
  description: string;
  election_type: string;
  scope_unit: OrganizationalUnitSummary;
  status: string;
  organized_by: UserSummary;
  start_date: string;
  end_date: string;
  created_at: string;
}

export interface DashboardEvent {
  id: string;
  title: string;
  description: string;
  event_type: string;
  campaign: { id: string; title: string } | null;
  target_unit: OrganizationalUnitSummary;
  organizer: UserSummary;
  location: string;
  scheduled_start: string;
  scheduled_end: string;
  status: string;
  created_at: string;
}

export interface FinanceCategoryTotal {
  record_type: string;
  category: string;
  total: string;
}

export interface FinanceSummary {
  organizational_unit: OrganizationalUnitSummary;
  total_income: string;
  total_expense: string;
  net_balance: string;
  record_count: number;
  by_category: FinanceCategoryTotal[];
}

export interface JurisdictionSummary {
  organizational_unit: OrganizationalUnitSummary;
  total_members: number;
  executive_count: number;
  gender_breakdown: Record<string, number>;
  growth_last_12_months: { month: string; new_members: number }[];
  pending_complaints: number;
  pending_discipline_cases: number;
  pending_welfare_requests: number;
  requires_attention: number;
}

export interface DashboardPayload {
  profile: User;
  unread_notification_count: number;
  upcoming_meetings: Meeting[];
  recent_broadcasts: Broadcast[];
  pending_tasks: PendingTask[];
  teams_led?: TeamLed[];
  active_elections?: DashboardElection[];
  upcoming_events?: DashboardEvent[];
  finance_summary?: FinanceSummary;
  jurisdiction_summary?: JurisdictionSummary;
}

export async function fetchDashboard(): Promise<DashboardPayload> {
  const { data } = await apiClient.get<DashboardPayload>("/dashboard/");
  return data;
}
