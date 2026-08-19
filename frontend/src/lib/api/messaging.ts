import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export interface Notification {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  target_type: string | null;
  target_id: string | null;
  is_read: boolean;
  created_at: string;
}

export async function fetchNotifications(params?: {
  is_read?: boolean;
  page?: number;
}): Promise<PaginatedResponse<Notification>> {
  const { data } = await apiClient.get<PaginatedResponse<Notification>>(
    "/messaging/notifications/",
    { params },
  );
  return data;
}

export async function fetchUnreadCount(): Promise<number> {
  const { data } = await apiClient.get<{ unread_count: number }>(
    "/messaging/notifications/unread-count/",
  );
  return data.unread_count;
}

export async function markNotificationRead(id: string): Promise<void> {
  await apiClient.post(`/messaging/notifications/${id}/read/`);
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiClient.post("/messaging/notifications/mark-all-read/");
}

// ---- Broadcasts ----

export const BROADCAST_KIND_CHOICES = ["DIRECTIVE", "ANNOUNCEMENT"] as const;
export const PRIORITY_CHOICES = ["LOW", "NORMAL", "HIGH", "URGENT"] as const;

export interface Broadcast {
  id: string;
  title: string;
  body: string;
  kind: (typeof BROADCAST_KIND_CHOICES)[number];
  priority: (typeof PRIORITY_CHOICES)[number];
  issued_by: UserSummary;
  target_unit: OrganizationalUnitSummary;
  requires_acknowledgement: boolean;
  created_at: string;
}

export async function listBroadcasts(params?: {
  target_unit_id?: string;
  kind?: string;
  page?: number;
}): Promise<PaginatedResponse<Broadcast>> {
  const { data } = await apiClient.get<PaginatedResponse<Broadcast>>(
    "/messaging/broadcasts/",
    { params },
  );
  return data;
}

export async function createBroadcast(payload: {
  title: string;
  body: string;
  kind: string;
  priority?: string;
  target_unit_id: string;
  requires_acknowledgement?: boolean;
}): Promise<Broadcast> {
  const { data } = await apiClient.post<Broadcast>("/messaging/broadcasts/", payload);
  return data;
}

export async function acknowledgeBroadcast(id: string): Promise<void> {
  await apiClient.post(`/messaging/broadcasts/${id}/acknowledge/`);
}

export async function getBroadcastAcknowledgements(id: string): Promise<{
  total_recipients: number;
  acknowledged_count: number;
  acknowledgements: { user: UserSummary; acknowledged_at: string }[];
}> {
  const { data } = await apiClient.get(`/messaging/broadcasts/${id}/acknowledgements/`);
  return data;
}

// ---- Reports ----

export const REPORT_STATUS_CHOICES = ["SUBMITTED", "ACKNOWLEDGED", "RESOLVED"] as const;

export interface Report {
  id: string;
  title: string;
  body: string;
  submitted_by: UserSummary;
  submitting_unit: OrganizationalUnitSummary;
  target_unit: OrganizationalUnitSummary;
  status: (typeof REPORT_STATUS_CHOICES)[number];
  resolved_by: UserSummary | null;
  resolution_notes: string;
  created_at: string;
}

export async function listReports(params?: {
  status?: string;
  target_unit_id?: string;
  submitting_unit_id?: string;
  page?: number;
}): Promise<PaginatedResponse<Report>> {
  const { data } = await apiClient.get<PaginatedResponse<Report>>("/messaging/reports/", {
    params,
  });
  return data;
}

export async function createReport(payload: {
  title: string;
  body: string;
  target_unit_id: string;
}): Promise<Report> {
  const { data } = await apiClient.post<Report>("/messaging/reports/", payload);
  return data;
}

export async function updateReportStatus(
  id: string,
  status: "ACKNOWLEDGED" | "RESOLVED",
  resolutionNotes?: string,
): Promise<Report> {
  const { data } = await apiClient.patch<Report>(`/messaging/reports/${id}/`, {
    status,
    resolution_notes: resolutionNotes,
  });
  return data;
}

// ---- Meetings ----

export const MEETING_TYPE_CHOICES = ["MEETING", "WORKSHOP"] as const;
export const MEETING_STATUS_CHOICES = ["SCHEDULED", "LIVE", "COMPLETED", "CANCELLED"] as const;
export const RSVP_STATUS_CHOICES = ["ATTENDING", "DECLINED"] as const;

export interface Meeting {
  id: string;
  title: string;
  description: string;
  meeting_type: (typeof MEETING_TYPE_CHOICES)[number];
  department: { id: string; name: string } | null;
  target_unit: OrganizationalUnitSummary;
  host: UserSummary;
  scheduled_start: string;
  scheduled_end: string;
  meeting_url: string;
  status: (typeof MEETING_STATUS_CHOICES)[number];
  created_at: string;
}

export async function listMeetings(params?: {
  department_id?: string;
  target_unit_id?: string;
  status?: string;
  upcoming?: boolean;
  page?: number;
}): Promise<PaginatedResponse<Meeting>> {
  const { data } = await apiClient.get<PaginatedResponse<Meeting>>("/messaging/meetings/", {
    params,
  });
  return data;
}

export async function getMeeting(id: string): Promise<Meeting> {
  const { data } = await apiClient.get<Meeting>(`/messaging/meetings/${id}/`);
  return data;
}

export async function createMeeting(payload: {
  title: string;
  description?: string;
  meeting_type: string;
  department_id?: string | null;
  target_unit_id: string;
  scheduled_start: string;
  scheduled_end: string;
}): Promise<Meeting> {
  const { data } = await apiClient.post<Meeting>("/messaging/meetings/", payload);
  return data;
}

export async function updateMeetingStatus(
  id: string,
  status: "LIVE" | "COMPLETED" | "CANCELLED",
): Promise<Meeting> {
  const { data } = await apiClient.patch<Meeting>(`/messaging/meetings/${id}/`, { status });
  return data;
}

export async function rsvpToMeeting(
  id: string,
  status: "ATTENDING" | "DECLINED",
): Promise<void> {
  await apiClient.post(`/messaging/meetings/${id}/rsvp/`, { status });
}

export async function getMeetingRsvps(id: string): Promise<{
  total_invited: number;
  attending_count: number;
  declined_count: number;
  rsvps: { user: UserSummary; status: string; responded_at: string }[];
}> {
  const { data } = await apiClient.get(`/messaging/meetings/${id}/rsvps/`);
  return data;
}

export interface MeetingMinutes {
  id: string;
  meeting_id: string;
  recorded_by: UserSummary;
  summary: string;
  decisions: string;
  attendees: UserSummary[];
  action_items: {
    description: string;
    assigned_to: UserSummary | null;
    due_date: string | null;
    is_done: boolean;
  }[];
  created_at: string;
}

export async function getMeetingMinutes(id: string): Promise<MeetingMinutes> {
  const { data } = await apiClient.get<MeetingMinutes>(`/messaging/meetings/${id}/minutes/`);
  return data;
}

export async function recordMeetingMinutes(
  id: string,
  payload: {
    summary?: string;
    decisions?: string;
    action_items?: { description: string; assigned_to_id?: string | null }[];
  },
): Promise<MeetingMinutes> {
  const { data } = await apiClient.post<MeetingMinutes>(
    `/messaging/meetings/${id}/minutes/`,
    payload,
  );
  return data;
}

// ---- Notification preferences ----

export interface NotificationPreference {
  email_enabled: boolean;
  sms_enabled: boolean;
  push_enabled: boolean;
  push_token: string | null;
}

export async function getNotificationPreferences(): Promise<NotificationPreference> {
  const { data } = await apiClient.get<NotificationPreference>(
    "/messaging/notification-preferences/",
  );
  return data;
}

export async function updateNotificationPreferences(
  payload: Partial<NotificationPreference>,
): Promise<NotificationPreference> {
  const { data } = await apiClient.put<NotificationPreference>(
    "/messaging/notification-preferences/",
    payload,
  );
  return data;
}
