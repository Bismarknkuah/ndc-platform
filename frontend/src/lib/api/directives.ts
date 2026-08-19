import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

export interface Directive {
  id: string;
  assigned_to: {
    id: string;
    full_name: string;
    role: string | null;
    organizational_unit: string | null;
  };
  assigned_by: {
    id: string;
    full_name: string;
  };
  title: string;
  description: string;
  due_at: string | null;
  status: "PENDING" | "ACKNOWLEDGED" | "COMPLETED";
  acknowledged_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export async function fetchMyDirectives(): Promise<PaginatedResponse<Directive>> {
  const { data } = await apiClient.get<PaginatedResponse<Directive>>(
    "/executive-ai/directives/",
  );
  return data;
}

export async function fetchIssuedDirectives(): Promise<PaginatedResponse<Directive>> {
  const { data } = await apiClient.get<PaginatedResponse<Directive>>(
    "/executive-ai/directives/issued/",
  );
  return data;
}

export async function assignDirective(payload: {
  assigned_to_id: string;
  title: string;
  description?: string;
  due_at?: string;
}): Promise<Directive> {
  const { data } = await apiClient.post<Directive>("/executive-ai/directives/", payload);
  return data;
}

export async function acknowledgeDirective(id: string): Promise<Directive> {
  const { data } = await apiClient.post<Directive>(
    `/executive-ai/directives/${id}/acknowledge/`,
  );
  return data;
}

export async function completeDirective(id: string): Promise<Directive> {
  const { data } = await apiClient.post<Directive>(`/executive-ai/directives/${id}/complete/`);
  return data;
}
