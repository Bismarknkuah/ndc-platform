import { apiClient } from "./client";

export async function draftBroadcast(topic: string, tone?: string): Promise<string> {
  const { data } = await apiClient.post<{ draft: string }>("/executive-ai/draft-broadcast/", {
    topic,
    tone,
  });
  return data.draft;
}

export async function summarizePendingItems(jurisdictionSummary: unknown): Promise<string> {
  const { data } = await apiClient.post<{ summary: string }>(
    "/executive-ai/summarize-pending/",
    { jurisdiction_summary: jurisdictionSummary },
  );
  return data.summary;
}

export async function generateMeetingAgenda(
  meetingTopic: string,
  context?: string,
): Promise<string> {
  const { data } = await apiClient.post<{ agenda: string }>("/executive-ai/meeting-agenda/", {
    meeting_topic: meetingTopic,
    context,
  });
  return data.agenda;
}
