import { apiClient } from "./client";
import type { OrganizationalUnitSummary } from "./types";

export interface MembershipAnalytics {
  organizational_unit: OrganizationalUnitSummary;
  total_members: number;
  executive_count: number;
  ordinary_member_count: number;
  gender_breakdown: { MALE: number; FEMALE: number; OTHER: number; UNSPECIFIED: number };
  growth_last_12_months: { month: string; new_members: number }[];
}

export async function getMembershipAnalytics(
  organizationalUnitId: string,
): Promise<MembershipAnalytics> {
  const { data } = await apiClient.get<MembershipAnalytics>("/analytics/membership/", {
    params: { organizational_unit_id: organizationalUnitId },
  });
  return data;
}

export interface DepartmentAnalytics {
  department: { id: string; name: string };
  organizational_unit: OrganizationalUnitSummary;
  team_size: number;
  total_tasks: number;
  status_breakdown: {
    PENDING: number;
    ACKNOWLEDGED: number;
    COMPLETED: number;
    CANCELLED: number;
  };
  completion_rate_percentage: number | null;
}

export async function getDepartmentAnalytics(
  departmentId: string,
  organizationalUnitId: string,
): Promise<DepartmentAnalytics> {
  const { data } = await apiClient.get<DepartmentAnalytics>("/analytics/departments/", {
    params: { department_id: departmentId, organizational_unit_id: organizationalUnitId },
  });
  return data;
}

export interface GeoJSONFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: { id: string; name: string; unit_type: string };
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

export async function getGISMap(
  organizationalUnitId: string,
  unitType?: string,
): Promise<GeoJSONFeatureCollection> {
  const { data } = await apiClient.get<GeoJSONFeatureCollection>("/analytics/map/", {
    params: { organizational_unit_id: organizationalUnitId, unit_type: unitType },
  });
  return data;
}
