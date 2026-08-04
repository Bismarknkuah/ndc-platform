import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

export interface AuditLogEntry {
  id: string;
  actor_email: string;
  actor_role: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  description: string;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export async function listAuditLogs(params?: {
  action?: string;
  actor_id?: string;
  target_type?: string;
  page?: number;
}): Promise<PaginatedResponse<AuditLogEntry>> {
  const { data } = await apiClient.get<PaginatedResponse<AuditLogEntry>>("/audit/logs/", {
    params,
  });
  return data;
}
