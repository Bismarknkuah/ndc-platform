import { apiClient } from "./client";
import type { PaginatedResponse, OrganizationalUnitSummary } from "./types";

interface UserSummary {
  id: string;
  full_name: string;
  membership_id: string;
}

export const RECORD_TYPE_CHOICES = ["INCOME", "EXPENSE"] as const;
export const RECORD_STATUS_CHOICES = ["PENDING", "APPROVED", "REJECTED"] as const;
export const COMMON_CATEGORIES = [
  "Membership Dues",
  "Donations",
  "Fundraising Event",
  "Event Costs",
  "Campaign Materials",
  "Travel & Logistics",
  "Administrative",
  "Salaries & Stipends",
  "Welfare Support",
  "Other",
];

export interface FinanceRecord {
  id: string;
  record_type: (typeof RECORD_TYPE_CHOICES)[number];
  category: string;
  amount: string;
  currency: string;
  description: string;
  organizational_unit: OrganizationalUnitSummary;
  recorded_by: UserSummary;
  record_date: string;
  receipt_photo_base64: string | null;
  status: (typeof RECORD_STATUS_CHOICES)[number];
  approved_by: UserSummary | null;
  approved_at: string | null;
  created_at: string;
}

export async function listFinanceRecords(params: {
  organizational_unit_id: string;
  record_type?: string;
  status?: string;
  page?: number;
}): Promise<PaginatedResponse<FinanceRecord>> {
  const { data } = await apiClient.get<PaginatedResponse<FinanceRecord>>(
    "/finance/records/",
    { params },
  );
  return data;
}

export async function createFinanceRecord(payload: {
  record_type: string;
  category: string;
  amount: string;
  currency?: string;
  description?: string;
  organizational_unit_id: string;
  receipt_photo_base64?: string | null;
}): Promise<FinanceRecord> {
  const { data } = await apiClient.post<FinanceRecord>("/finance/records/", payload);
  return data;
}

export async function updateFinanceRecordStatus(
  id: string,
  status: "APPROVED" | "REJECTED",
): Promise<FinanceRecord> {
  const { data } = await apiClient.patch<FinanceRecord>(`/finance/records/${id}/`, { status });
  return data;
}

export interface FinanceCategoryTotal {
  record_type: string;
  category: string;
  total: string;
}

export interface FinanceSummary {
  organizational_unit: OrganizationalUnitSummary;
  total_income: string;
  total_expense: string;
  net_balance: string;
  record_count: number;
  by_category: FinanceCategoryTotal[];
}

export async function getFinanceSummary(
  organizationalUnitId: string,
  statusFilter: "APPROVED" | "ALL" = "APPROVED",
): Promise<FinanceSummary> {
  const { data } = await apiClient.get<FinanceSummary>("/finance/summary/", {
    params: { organizational_unit_id: organizationalUnitId, status: statusFilter },
  });
  return data;
}
