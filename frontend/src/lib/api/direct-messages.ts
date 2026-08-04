import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export interface DirectMessage {
  id: string;
  sender: UserSummary;
  recipient: UserSummary;
  body: string;
  read_at: string | null;
  created_at: string;
}

/** Omit `withUserId` to get every DM sent to/from the caller (used to
 * build the inbox's conversation list client-side); pass it to get one
 * conversation's full thread. */
export async function listDirectMessages(
  withUserId?: string,
  page?: number,
): Promise<PaginatedResponse<DirectMessage>> {
  const { data } = await apiClient.get<PaginatedResponse<DirectMessage>>(
    "/messaging/direct-messages/",
    { params: { with: withUserId, page } },
  );
  return data;
}

export async function sendDirectMessage(
  recipientId: string,
  body: string,
): Promise<DirectMessage> {
  const { data } = await apiClient.post<DirectMessage>("/messaging/direct-messages/", {
    recipient_id: recipientId,
    body,
  });
  return data;
}

export async function markDirectMessageRead(id: string): Promise<DirectMessage> {
  const { data } = await apiClient.post<DirectMessage>(
    `/messaging/direct-messages/${id}/read/`,
  );
  return data;
}
