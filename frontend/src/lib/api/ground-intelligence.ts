import { apiClient } from "./client";

interface OrganizationalUnitSummary {
  id: string;
  name: string;
  unit_type: string;
}

export interface GroundIntelligenceItem {
  description?: string;
  body?: string;
  status: string;
  unit: string | null;
  created_at: string;
}

export interface GroundIntelligence {
  organizational_unit: OrganizationalUnitSummary;
  counts: {
    pending_complaints: number;
    pending_welfare_requests: number;
    pending_discipline_cases: number;
    total_reports: number;
  };
  recent_complaints: (GroundIntelligenceItem & { subject: string; type: string })[];
  recent_welfare_requests: (GroundIntelligenceItem & { category: string })[];
  recent_reports: (GroundIntelligenceItem & { title: string })[];
}

export async function fetchGroundIntelligence(unitId: string): Promise<GroundIntelligence> {
  const { data } = await apiClient.get<GroundIntelligence>(
    `/analytics/ground-intelligence/${unitId}/`,
  );
  return data;
}

export async function fetchGroundBriefing(
  unitId: string,
): Promise<{ briefing: string; ground_intelligence: GroundIntelligence }> {
  const { data } = await apiClient.post<{
    briefing: string;
    ground_intelligence: GroundIntelligence;
  }>(`/executive-ai/ground-briefing/${unitId}/`);
  return data;
}
