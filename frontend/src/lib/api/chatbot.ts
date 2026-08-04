import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

export interface ChatConversation {
  id: string;
  title: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: "USER" | "ASSISTANT";
  body: string;
  created_at: string;
}

export interface SendMessageResponse {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export async function listConversations(): Promise<PaginatedResponse<ChatConversation>> {
  const { data } = await apiClient.get<PaginatedResponse<ChatConversation>>(
    "/chatbot/conversations/",
  );
  return data;
}

export async function createConversation(title?: string): Promise<ChatConversation> {
  const { data } = await apiClient.post<ChatConversation>("/chatbot/conversations/", {
    title,
  });
  return data;
}

export async function archiveConversation(id: string): Promise<void> {
  await apiClient.delete(`/chatbot/conversations/${id}/`);
}

export async function listMessages(
  conversationId: string,
): Promise<PaginatedResponse<ChatMessage>> {
  const { data } = await apiClient.get<PaginatedResponse<ChatMessage>>(
    `/chatbot/conversations/${conversationId}/messages/`,
  );
  return data;
}

export async function sendMessage(
  conversationId: string,
  body: string,
): Promise<SendMessageResponse> {
  const { data } = await apiClient.post<SendMessageResponse>(
    `/chatbot/conversations/${conversationId}/messages/`,
    { body },
  );
  return data;
}
