import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export interface DiscussionGroup {
  id: string;
  name: string;
  description: string;
  organizational_unit: OrganizationalUnitSummary | null;
  created_by: UserSummary;
  members: UserSummary[];
  is_active: boolean;
  created_at: string;
}

export async function listGroups(page?: number): Promise<PaginatedResponse<DiscussionGroup>> {
  const { data } = await apiClient.get<PaginatedResponse<DiscussionGroup>>(
    "/messaging/groups/",
    { params: { page } },
  );
  return data;
}

export async function createGroup(payload: {
  name: string;
  description?: string;
  organizational_unit_id?: string | null;
  member_ids?: string[];
}): Promise<DiscussionGroup> {
  const { data } = await apiClient.post<DiscussionGroup>("/messaging/groups/", payload);
  return data;
}

export async function addGroupMember(groupId: string, userId: string): Promise<DiscussionGroup> {
  const { data } = await apiClient.post<DiscussionGroup>(
    `/messaging/groups/${groupId}/members/`,
    { user_id: userId },
  );
  return data;
}

export async function removeGroupMember(
  groupId: string,
  userId: string,
): Promise<DiscussionGroup> {
  const { data } = await apiClient.delete<DiscussionGroup>(
    `/messaging/groups/${groupId}/members/`,
    { data: { user_id: userId } },
  );
  return data;
}

export interface GroupMessage {
  id: string;
  sender: UserSummary;
  body: string;
  created_at: string;
}

export async function listGroupMessages(
  groupId: string,
  page?: number,
): Promise<PaginatedResponse<GroupMessage>> {
  const { data } = await apiClient.get<PaginatedResponse<GroupMessage>>(
    `/messaging/groups/${groupId}/messages/`,
    { params: { page } },
  );
  return data;
}

export async function sendGroupMessage(groupId: string, body: string): Promise<GroupMessage> {
  const { data } = await apiClient.post<GroupMessage>(
    `/messaging/groups/${groupId}/messages/`,
    { body },
  );
  return data;
}
