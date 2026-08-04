import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

export const POSITION_CHOICES = ["HEAD", "DEPUTY_HEAD", "OFFICER", "MEMBER"] as const;
export const ENGAGEMENT_TYPE_CHOICES = ["TV", "RADIO", "PRINT", "ONLINE", "EVENT", "OTHER"] as const;
export const TASK_STATUS_CHOICES = ["PENDING", "ACKNOWLEDGED", "COMPLETED", "CANCELLED"] as const;

export interface Department {
  id: string;
  name: string;
  code: string;
  description: string;
  is_active: boolean;
}

interface UserSummary {
  id: string;
  full_name: string;
  email: string;
  membership_id?: string;
}

export interface DepartmentAssignment {
  id: string;
  user: UserSummary;
  department: { id: string; name: string; code: string };
  organizational_unit: { id: string; name: string; unit_type: string };
  position: (typeof POSITION_CHOICES)[number];
  appointed_by: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TaskAssignment {
  id: string;
  department: { id: string; name: string };
  assigned_to: { id: string; full_name: string };
  assigned_by: { id: string; full_name: string };
  title: string;
  description: string;
  engagement_type: (typeof ENGAGEMENT_TYPE_CHOICES)[number];
  platform_name: string;
  location: string;
  scheduled_at: string;
  status: (typeof TASK_STATUS_CHOICES)[number];
  acknowledged_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TeamRosterMember {
  user: UserSummary;
  position: string;
  pending_tasks: number;
  completed_tasks_this_week: number;
}

export interface TeamDashboard {
  department: { id: string; name: string; code: string };
  organizational_unit: { id: string; name: string; unit_type: string };
  team_size: number;
  roster: TeamRosterMember[];
  upcoming_tasks: TaskAssignment[];
  total_pending_tasks: number;
}

export async function listDepartments(): Promise<Department[]> {
  const { data } = await apiClient.get<Department[]>("/departments/");
  return data;
}

export async function createDepartment(payload: {
  name: string;
  code: string;
  description?: string;
}): Promise<Department> {
  const { data } = await apiClient.post<Department>("/departments/", payload);
  return data;
}

export async function listAssignments(params?: {
  department_id?: string;
  organizational_unit_id?: string;
  user_id?: string;
  page?: number;
}): Promise<PaginatedResponse<DepartmentAssignment>> {
  const { data } = await apiClient.get<PaginatedResponse<DepartmentAssignment>>(
    "/departments/assignments/",
    { params },
  );
  return data;
}

export async function createAssignment(payload: {
  user_id: string;
  department_id: string;
  organizational_unit_id: string;
  position: string;
}): Promise<DepartmentAssignment> {
  const { data } = await apiClient.post<DepartmentAssignment>(
    "/departments/assignments/",
    payload,
  );
  return data;
}

export async function removeAssignment(id: string): Promise<void> {
  await apiClient.delete(`/departments/assignments/${id}/`);
}

export async function myAssignments(): Promise<DepartmentAssignment[]> {
  const { data } = await apiClient.get<DepartmentAssignment[]>(
    "/departments/my-assignments/",
  );
  return data;
}

export async function getTeamDashboard(
  departmentId: string,
  organizationalUnitId: string,
): Promise<TeamDashboard> {
  const { data } = await apiClient.get<TeamDashboard>("/departments/dashboard/", {
    params: { department_id: departmentId, organizational_unit_id: organizationalUnitId },
  });
  return data;
}

export interface TaskListParams {
  assigned_to_id?: string;
  department_id?: string;
  status?: string;
  page?: number;
}

export async function listTasks(
  params?: TaskListParams,
): Promise<PaginatedResponse<TaskAssignment>> {
  const { data } = await apiClient.get<PaginatedResponse<TaskAssignment>>(
    "/departments/tasks/",
    { params },
  );
  return data;
}

export async function createTask(payload: {
  department_id: string;
  assigned_to_id: string;
  title: string;
  description?: string;
  engagement_type: string;
  platform_name?: string;
  location?: string;
  scheduled_at: string;
}): Promise<TaskAssignment> {
  const { data } = await apiClient.post<TaskAssignment>("/departments/tasks/", payload);
  return data;
}

export async function updateTaskStatus(
  id: string,
  status: "ACKNOWLEDGED" | "COMPLETED" | "CANCELLED",
): Promise<TaskAssignment> {
  const { data } = await apiClient.patch<TaskAssignment>(`/departments/tasks/${id}/`, {
    status,
  });
  return data;
}
