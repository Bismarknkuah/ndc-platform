import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const ELECTION_TYPE_CHOICES = [
  "NATIONAL_GENERAL",
  "PARTY_INTERNAL",
  "POLL",
  "OTHER",
] as const;
export const ELECTION_STATUS_CHOICES = [
  "DRAFT",
  "OPEN",
  "COLLATION",
  "COMPLETED",
  "CANCELLED",
] as const;
export const RESULT_STATUS_CHOICES = ["SUBMITTED", "VERIFIED", "DISPUTED"] as const;
export const POLLING_AGENT_ROLE_CHOICES = [
  "PARTY_AGENT",
  "PRESIDING_OFFICER_LIAISON",
  "OBSERVER",
] as const;

export interface Election {
  id: string;
  title: string;
  description: string;
  election_type: (typeof ELECTION_TYPE_CHOICES)[number];
  scope_unit: OrganizationalUnitSummary;
  status: (typeof ELECTION_STATUS_CHOICES)[number];
  organized_by: UserSummary;
  start_date: string;
  end_date: string;
  created_at: string;
}

export async function listElections(params?: {
  election_type?: string;
  status?: string;
  scope_unit_id?: string;
  page?: number;
}): Promise<PaginatedResponse<Election>> {
  const { data } = await apiClient.get<PaginatedResponse<Election>>("/elections/", {
    params,
  });
  return data;
}

export async function getElection(id: string): Promise<Election> {
  const { data } = await apiClient.get<Election>(`/elections/${id}/`);
  return data;
}

export async function createElection(payload: {
  title: string;
  description?: string;
  election_type: string;
  scope_unit_id: string;
  start_date: string;
  end_date: string;
}): Promise<Election> {
  const { data } = await apiClient.post<Election>("/elections/", payload);
  return data;
}

export async function updateElectionStatus(
  id: string,
  status: "OPEN" | "COLLATION" | "COMPLETED" | "CANCELLED",
): Promise<Election> {
  const { data } = await apiClient.patch<Election>(`/elections/${id}/`, { status });
  return data;
}

// ---- Candidates ----

export interface Candidate {
  id: string;
  name: string;
  description: string;
  position: string | null;
  party: string | null;
  display_order: number;
  photo_base64: string | null;
}

export async function listCandidates(electionId: string, position?: string): Promise<Candidate[]> {
  const { data } = await apiClient.get<Candidate[]>(`/elections/${electionId}/candidates/`, {
    params: position ? { position } : undefined,
  });
  return data;
}

export async function createCandidate(
  electionId: string,
  payload: {
    name: string;
    description?: string;
    position?: string | null;
    party?: string | null;
    display_order?: number;
    photo_base64?: string | null;
  },
): Promise<Candidate> {
  const { data } = await apiClient.post<Candidate>(
    `/elections/${electionId}/candidates/`,
    payload,
  );
  return data;
}

// ---- Result submissions (branch collation) ----

export interface CandidateTally {
  candidate_id: string;
  candidate_name: string;
  party: string | null;
  votes: number;
}

export interface ResultSubmission {
  id: string;
  election_id: string;
  branch_unit: OrganizationalUnitSummary;
  position: string | null;
  tallies: CandidateTally[];
  collation_sheet_photo_base64: string;
  total_registered_voters: number | null;
  total_valid_votes: number | null;
  total_rejected_votes: number | null;
  submitted_by: UserSummary;
  status: (typeof RESULT_STATUS_CHOICES)[number];
  verified_by: UserSummary | null;
  verified_at: string | null;
  created_at: string;
}

export async function listResults(params: {
  election_id?: string;
  branch_unit_id?: string;
  organizational_unit_id?: string;
  status?: string;
  page?: number;
}): Promise<PaginatedResponse<ResultSubmission>> {
  const { data } = await apiClient.get<PaginatedResponse<ResultSubmission>>(
    "/elections/results/",
    { params },
  );
  return data;
}

export async function submitResult(payload: {
  election_id: string;
  branch_unit_id: string;
  position?: string | null;
  tallies: { candidate_id: string; votes: number }[];
  collation_sheet_photo_base64: string;
  total_registered_voters?: number;
  total_valid_votes?: number;
  total_rejected_votes?: number;
}): Promise<ResultSubmission> {
  const { data } = await apiClient.post<ResultSubmission>("/elections/results/", payload);
  return data;
}

export async function verifyResult(
  id: string,
  status: "VERIFIED" | "DISPUTED",
): Promise<ResultSubmission> {
  const { data } = await apiClient.patch<ResultSubmission>(`/elections/results/${id}/`, {
    status,
  });
  return data;
}

// ---- Automatic summary ----

export interface CandidateResult {
  candidate_id: string;
  candidate_name: string;
  party: string | null;
  votes: number;
  percentage: number;
}

export interface PartyResult {
  party: string;
  votes: number;
  percentage: number;
}

export interface ResultSummary {
  election_id: string;
  organizational_unit: OrganizationalUnitSummary;
  position: string | null;
  mode: "BRANCH_COLLATION" | "DIRECT_VOTING";
  results: CandidateResult[];
  party_results: PartyResult[];
  leading_candidate: CandidateResult | null;
  total_votes_cast: number;
  is_fully_reported: boolean;
  // BRANCH_COLLATION only:
  total_registered_voters?: number | null;
  total_valid_votes?: number | null;
  total_rejected_votes?: number | null;
  turnout_percentage?: number | null;
  branches_expected?: number;
  branches_reported?: number;
  reporting_percentage?: number | null;
  verified_submissions?: number;
  disputed_submissions?: number;
  // DIRECT_VOTING only:
  eligible_voters_count?: number;
  votes_cast_count?: number;
}

export async function getResultSummary(
  electionId: string,
  organizationalUnitId: string,
  position?: string,
): Promise<ResultSummary> {
  const { data } = await apiClient.get<ResultSummary>(
    `/elections/${electionId}/results/summary/`,
    { params: { organizational_unit_id: organizationalUnitId, position } },
  );
  return data;
}

// ---- Direct voting / electorate ----

export interface EligibleVoter {
  id: string;
  user: UserSummary;
  added_by: UserSummary;
  created_at: string;
}

export async function listEligibleVoters(electionId: string): Promise<EligibleVoter[]> {
  const { data } = await apiClient.get<EligibleVoter[]>(`/elections/${electionId}/voters/`);
  return data;
}

export async function addEligibleVoters(
  electionId: string,
  userIds: string[],
): Promise<EligibleVoter[]> {
  const { data } = await apiClient.post<EligibleVoter[]>(`/elections/${electionId}/voters/`, {
    user_ids: userIds,
  });
  return data;
}

export async function removeEligibleVoter(electionId: string, userId: string): Promise<void> {
  await apiClient.delete(`/elections/${electionId}/voters/${userId}/`);
}

export interface MyEligibility {
  eligible: boolean;
  election_status: string;
  voted_positions: (string | null)[];
}

export async function getMyEligibility(electionId: string): Promise<MyEligibility> {
  const { data } = await apiClient.get<MyEligibility>(
    `/elections/${electionId}/my-eligibility/`,
  );
  return data;
}

export async function castVote(
  electionId: string,
  candidateId: string,
  position?: string | null,
): Promise<{
  id: string;
  election_id: string;
  position: string | null;
  candidate: { id: string; name: string };
  cast_at: string;
}> {
  const { data } = await apiClient.post(`/elections/${electionId}/vote/`, {
    candidate_id: candidateId,
    position,
  });
  return data;
}

// ---- Polling agents ----

export interface PollingAgentAssignment {
  id: string;
  election_id: string;
  branch_unit: OrganizationalUnitSummary;
  agent: UserSummary;
  role: (typeof POLLING_AGENT_ROLE_CHOICES)[number];
  assigned_by: UserSummary;
  checked_in_at: string | null;
  materials_confirmed: boolean;
  notes: string;
  created_at: string;
}

export async function listPollingAgents(params: {
  election_id?: string;
  branch_unit_id?: string;
  page?: number;
}): Promise<PaginatedResponse<PollingAgentAssignment>> {
  const { data } = await apiClient.get<PaginatedResponse<PollingAgentAssignment>>(
    "/elections/agents/",
    { params },
  );
  return data;
}

export async function assignPollingAgent(payload: {
  election_id: string;
  branch_unit_id: string;
  agent_id: string;
  role: string;
  notes?: string;
}): Promise<PollingAgentAssignment> {
  const { data } = await apiClient.post<PollingAgentAssignment>("/elections/agents/", payload);
  return data;
}

export async function checkInPollingAgent(
  assignmentId: string,
  materialsConfirmed?: boolean,
): Promise<PollingAgentAssignment> {
  const { data } = await apiClient.post<PollingAgentAssignment>(
    `/elections/agents/${assignmentId}/check-in/`,
    { materials_confirmed: materialsConfirmed },
  );
  return data;
}
