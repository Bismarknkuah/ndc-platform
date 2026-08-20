import { apiClient } from "./client";

export type AiResponseSource = "ai" | "rule_based";

export async function draftBroadcast(
  topic: string,
  tone?: string,
): Promise<{ text: string; source: AiResponseSource }> {
  const { data } = await apiClient.post<{ draft: string; source: AiResponseSource }>(
    "/executive-ai/draft-broadcast/",
    { topic, tone },
  );
  return { text: data.draft, source: data.source };
}

export async function summarizePendingItems(
  jurisdictionSummary: unknown,
): Promise<{ text: string; source: AiResponseSource }> {
  const { data } = await apiClient.post<{ summary: string; source: AiResponseSource }>(
    "/executive-ai/summarize-pending/",
    { jurisdiction_summary: jurisdictionSummary },
  );
  return { text: data.summary, source: data.source };
}

export async function generateMeetingAgenda(
  meetingTopic: string,
  context?: string,
): Promise<{ text: string; source: AiResponseSource }> {
  const { data } = await apiClient.post<{ agenda: string; source: AiResponseSource }>(
    "/executive-ai/meeting-agenda/",
    { meeting_topic: meetingTopic, context },
  );
  return { text: data.agenda, source: data.source };
}
