import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const DISCIPLINE_GROUND_CHOICES = [
  "CONSTITUTIONAL_BREACH",
  "ANTI_PARTY_CONDUCT",
  "INSUBORDINATION",
  "CONFIDENTIALITY_BREACH",
  "OTHER",
] as const;

export const DISCIPLINARY_MEASURE_CHOICES = [
  "EXPULSION",
  "SUSPENSION",
  "REMOVAL_FROM_OFFICE",
  "INELIGIBILITY",
  "FINE",
  "REPRIMAND",
] as const;

export const CASE_STATUS_CHOICES = [
  "REPORTED",
  "CONVENED",
  "RECOMMENDED",
  "DECIDED",
  "APPEALED",
  "CLOSED",
] as const;

export interface DisciplinaryCommittee {
  id: string;
  organizational_unit: OrganizationalUnitSummary;
  members: UserSummary[];
  elected_at: string;
  is_active: boolean;
}

export async function listCommittees(
  organizationalUnitId: string,
): Promise<DisciplinaryCommittee[]> {
  const { data } = await apiClient.get<DisciplinaryCommittee[]>("/discipline/committees/", {
    params: { organizational_unit_id: organizationalUnitId },
  });
  return data;
}

export async function electCommittee(
  organizationalUnitId: string,
  memberIds: string[],
): Promise<DisciplinaryCommittee> {
  const { data } = await apiClient.post<DisciplinaryCommittee>("/discipline/committees/", {
    organizational_unit_id: organizationalUnitId,
    member_ids: memberIds,
  });
  return data;
}

export interface DisciplinaryCase {
  id: string;
  organizational_unit: OrganizationalUnitSummary;
  committee_id: string | null;
  respondent: UserSummary;
  reported_by: UserSummary;
  grounds: (typeof DISCIPLINE_GROUND_CHOICES)[number];
  description: string;
  status: (typeof CASE_STATUS_CHOICES)[number];
  reported_at: string;
  convened_at: string | null;
  convene_deadline: string;
  convene_overdue: boolean;
  conclude_deadline: string | null;
  conclude_overdue: boolean;
  recommendation: string;
  recommended_measure: (typeof DISCIPLINARY_MEASURE_CHOICES)[number] | null;
  recommended_at: string | null;
  final_decision: string;
  final_measure: (typeof DISCIPLINARY_MEASURE_CHOICES)[number] | null;
  decided_at: string | null;
  decided_by: UserSummary | null;
  varied_from_recommendation: boolean;
  appeal_deadline: string | null;
  parent_case_id: string | null;
  created_at: string;
}

export async function listCases(params?: {
  organizational_unit_id?: string;
  mine?: boolean;
  page?: number;
}): Promise<PaginatedResponse<DisciplinaryCase>> {
  const { data } = await apiClient.get<PaginatedResponse<DisciplinaryCase>>(
    "/discipline/cases/",
    { params },
  );
  return data;
}

export async function getCase(caseId: string): Promise<DisciplinaryCase> {
  const { data } = await apiClient.get<DisciplinaryCase>(`/discipline/cases/${caseId}/`);
  return data;
}

export async function reportCase(payload: {
  respondent_id: string;
  organizational_unit_id: string;
  grounds: string;
  description: string;
}): Promise<DisciplinaryCase> {
  const { data } = await apiClient.post<DisciplinaryCase>("/discipline/cases/", payload);
  return data;
}

export async function conveneCase(caseId: string): Promise<DisciplinaryCase> {
  const { data } = await apiClient.post<DisciplinaryCase>(
    `/discipline/cases/${caseId}/convene/`,
  );
  return data;
}

export async function recommendCase(
  caseId: string,
  recommendation: string,
  recommendedMeasure: string,
): Promise<DisciplinaryCase> {
  const { data } = await apiClient.post<DisciplinaryCase>(
    `/discipline/cases/${caseId}/recommend/`,
    { recommendation, recommended_measure: recommendedMeasure },
  );
  return data;
}

export async function decideCase(
  caseId: string,
  finalDecision: string,
  finalMeasure: string,
  confirmedTwoThirdsMajority?: boolean,
): Promise<DisciplinaryCase> {
  const { data } = await apiClient.post<DisciplinaryCase>(`/discipline/cases/${caseId}/decide/`, {
    final_decision: finalDecision,
    final_measure: finalMeasure,
    confirmed_two_thirds_majority: confirmedTwoThirdsMajority,
  });
  return data;
}

export async function appealCase(
  caseId: string,
  groundsForAppeal?: string,
): Promise<DisciplinaryCase> {
  const { data } = await apiClient.post<DisciplinaryCase>(`/discipline/cases/${caseId}/appeal/`, {
    grounds_for_appeal: groundsForAppeal,
  });
  return data;
}

export interface MemberSuspension {
  id: string;
  user: UserSummary;
  organizational_unit: OrganizationalUnitSummary;
  suspended_by: UserSummary;
  reason: string;
  status: "ACTIVE" | "REFERRED" | "LAPSED" | "ENDED";
  suspended_at: string;
  referred_at: string | null;
  referral_deadline: string;
  referral_overdue: boolean;
  renewed_at: string | null;
  renewal_count: number;
  related_case_id: string | null;
  created_at: string;
}

export async function listSuspensions(
  organizationalUnitId?: string,
): Promise<PaginatedResponse<MemberSuspension>> {
  const { data } = await apiClient.get<PaginatedResponse<MemberSuspension>>(
    "/discipline/suspensions/",
    {
      params: organizationalUnitId
        ? { organizational_unit_id: organizationalUnitId }
        : undefined,
    },
  );
  return data;
}

export async function imposeSuspension(userId: string, reason: string): Promise<MemberSuspension> {
  const { data } = await apiClient.post<MemberSuspension>("/discipline/suspensions/", {
    user_id: userId,
    reason,
  });
  return data;
}

export async function referSuspension(
  suspensionId: string,
  caseId: string,
): Promise<MemberSuspension> {
  const { data } = await apiClient.post<MemberSuspension>(
    `/discipline/suspensions/${suspensionId}/refer/`,
    { case_id: caseId },
  );
  return data;
}

export async function renewSuspension(suspensionId: string): Promise<MemberSuspension> {
  const { data } = await apiClient.post<MemberSuspension>(
    `/discipline/suspensions/${suspensionId}/renew/`,
  );
  return data;
}

export async function endSuspension(suspensionId: string): Promise<MemberSuspension> {
  const { data } = await apiClient.post<MemberSuspension>(
    `/discipline/suspensions/${suspensionId}/end/`,
  );
  return data;
}
