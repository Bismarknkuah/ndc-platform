import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export interface DuesPayment {
  id: string;
  user: UserSummary;
  amount: string;
  currency: string;
  period: string;
  status: "PENDING" | "SUCCESS" | "FAILED" | "ABANDONED";
  payment_method: string | null;
  paystack_reference: string;
  paid_at: string | null;
  created_at: string;
}

export async function initializeDuesPayment(
  amount: string,
  period?: string,
): Promise<{ authorization_url: string; reference: string }> {
  const { data } = await apiClient.post<{ authorization_url: string; reference: string }>(
    "/dues/initialize/",
    {
      amount,
      period,
      callback_url: typeof window !== "undefined" ? window.location.href : undefined,
    },
  );
  return data;
}

export async function verifyDuesPayment(reference: string): Promise<DuesPayment> {
  const { data } = await apiClient.get<DuesPayment>(`/dues/verify/${reference}/`);
  return data;
}

export async function fetchDuesHistory(page?: number): Promise<PaginatedResponse<DuesPayment>> {
  const { data } = await apiClient.get<PaginatedResponse<DuesPayment>>("/dues/history/", {
    params: { page },
  });
  return data;
}
