import { apiClient } from "./client";

export async function setKioskPin(currentPassword: string, pin: string): Promise<void> {
  await apiClient.post("/kiosk/my-pin/", {
    current_password: currentPassword,
    pin,
  });
}

export interface KioskVerifyResult {
  kiosk_vote_token: string;
  election_id: string;
  election_title: string;
  voter_name: string;
}

export async function verifyAtKiosk(
  kioskCode: string,
  membershipId: string,
  pin: string,
): Promise<KioskVerifyResult> {
  const { data } = await apiClient.post<KioskVerifyResult>("/kiosk/verify/", {
    kiosk_code: kioskCode,
    membership_id: membershipId,
    pin,
  });
  return data;
}

export async function castKioskVote(
  kioskVoteToken: string,
  candidateId: string,
  position?: string,
): Promise<void> {
  await apiClient.post("/kiosk/vote/", {
    kiosk_vote_token: kioskVoteToken,
    candidate_id: candidateId,
    position,
  });
}

export interface KioskRegistration {
  id: string;
  label: string;
  unit: { id: string; name: string };
  is_active: boolean;
  created_at: string;
  kiosk_code?: string;
}

export async function registerKiosk(
  electionId: string,
  unitId: string,
  label: string,
): Promise<KioskRegistration> {
  const { data } = await apiClient.post<KioskRegistration>(
    `/elections/${electionId}/kiosks/`,
    { unit_id: unitId, label },
  );
  return data;
}

export async function listKiosks(electionId: string): Promise<KioskRegistration[]> {
  const { data } = await apiClient.get<KioskRegistration[]>(
    `/elections/${electionId}/kiosks/`,
  );
  return data;
}
