import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

/**
 * Mirrors apps.hierarchy.constants exactly - see /home/claude/ndc-backend.
 * MAIN_CHAIN is the strict National->Branch chain, matching Article 11 of
 * the NDC Constitution exactly ("The Party shall be organised at branch,
 * constituency, regional and national level") - confirmed by reading the
 * actual constitution, not assumed. An earlier version of this hierarchy
 * had two extra invented levels (Electoral Area, Zone) that aren't real
 * constitutional levels; removed once the document was actually read.
 *
 * TEIN_CHAIN is its own 6-level chain (representation at Regional/Youth/
 * Women conferences is constitutionally confirmed; the specific internal
 * level names below "national" are an operational extension, not a direct
 * citation). AUXILIARY_TYPES (including DISTRICT_COORDINATING_COMMITTEE,
 * real per Article 17 but not one of the 4 official levels - it has no
 * conference or elected executive, and its membership is drawn *from*
 * constituency executives rather than containing them) attach flexibly
 * under any main-chain or TEIN unit. Names match Article 10's "Integral
 * Organs" list exactly (EXTERNAL_BRANCH and PARLIAMENTARY_GROUP were
 * originally DIASPORA_CHAPTER/PARLIAMENTARY_CAUCUS - renamed once the
 * full constitution was read). PROFESSIONALS_FORUM is not directly
 * confirmed in this (mini) constitution's 73 pages - a reasonable guess
 * at a Congress-created organ under Article 10(f), not a citation.
 */
export const MAIN_CHAIN = ["NATIONAL", "REGIONAL", "CONSTITUENCY", "BRANCH"] as const;

export const TEIN_CHAIN = [
  "TEIN_NATIONAL",
  "TEIN_REGIONAL",
  "TEIN_CAMPUS",
  "TEIN_FACULTY",
  "TEIN_DEPARTMENT",
  "TEIN_CLASS",
] as const;

export const AUXILIARY_TYPES = [
  "DISTRICT_COORDINATING_COMMITTEE",
  "WOMENS_WING",
  "YOUTH_WING",
  "ZONGO_CAUCUS",
  "EXTERNAL_BRANCH",
  "PARLIAMENTARY_GROUP",
  "COUNCIL_OF_ELDERS",
  "FUNCTIONAL_COMMITTEE",
  "PROFESSIONALS_FORUM",
] as const;

export const ALL_UNIT_TYPES = [...MAIN_CHAIN, ...TEIN_CHAIN, ...AUXILIARY_TYPES];

export function unitTypeLabel(unitType: string): string {
  return unitType
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}

/** The parent type required for a given unit_type within a strict chain,
 * or null for roots / auxiliary types (which attach flexibly). Mirrors
 * apps.hierarchy.constants.expected_parent_type exactly. */
export function expectedParentType(unitType: string): string | null {
  const mainIndex = (MAIN_CHAIN as readonly string[]).indexOf(unitType);
  if (mainIndex >= 0) return mainIndex > 0 ? MAIN_CHAIN[mainIndex - 1] : null;

  const teinIndex = (TEIN_CHAIN as readonly string[]).indexOf(unitType);
  if (teinIndex >= 0) return teinIndex > 0 ? TEIN_CHAIN[teinIndex - 1] : null;

  return null;
}

export interface OrganizationalUnit {
  id: string;
  name: string;
  code: string;
  unit_type: string;
  parent_id: string | null;
  parent_name: string | null;
  metadata: Record<string, unknown>;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UnitListParams {
  unit_type?: string;
  parent_id?: string;
  search?: string;
  page?: number;
}

export async function listUnits(
  params?: UnitListParams,
): Promise<PaginatedResponse<OrganizationalUnit>> {
  const { data } = await apiClient.get<PaginatedResponse<OrganizationalUnit>>(
    "/hierarchy/units/",
    { params },
  );
  return data;
}

export async function getUnit(id: string): Promise<OrganizationalUnit> {
  const { data } = await apiClient.get<OrganizationalUnit>(`/hierarchy/units/${id}/`);
  return data;
}

export async function getUnitAncestors(id: string): Promise<OrganizationalUnit[]> {
  const { data } = await apiClient.get<OrganizationalUnit[]>(
    `/hierarchy/units/${id}/ancestors/`,
  );
  return data;
}

export async function getUnitDescendants(id: string): Promise<OrganizationalUnit[]> {
  const { data } = await apiClient.get<OrganizationalUnit[]>(
    `/hierarchy/units/${id}/descendants/`,
  );
  return data;
}

export interface CreateUnitPayload {
  name: string;
  code: string;
  unit_type: string;
  parent_id?: string | null;
  metadata?: Record<string, unknown>;
  latitude?: number | null;
  longitude?: number | null;
}

export async function createUnit(payload: CreateUnitPayload): Promise<OrganizationalUnit> {
  const { data } = await apiClient.post<OrganizationalUnit>("/hierarchy/units/", payload);
  return data;
}

export async function updateUnit(
  id: string,
  payload: Partial<CreateUnitPayload>,
): Promise<OrganizationalUnit> {
  const { data } = await apiClient.patch<OrganizationalUnit>(
    `/hierarchy/units/${id}/`,
    payload,
  );
  return data;
}

export async function deactivateUnit(id: string): Promise<void> {
  await apiClient.delete(`/hierarchy/units/${id}/`);
}
