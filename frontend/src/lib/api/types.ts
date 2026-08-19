// Mirrors apps.accounts.serializers.{RoleSerializer,UserSerializer} and
// apps.hierarchy.serializers.OrganizationalUnitSerializer exactly - see
// /home/claude/ndc-backend for source of truth. Do not add fields the
// backend doesn't actually return.

export interface RoleSummary {
  id: string;
  name: string;
  code: string;
  scope: string;
  is_executive: boolean;
  is_active: boolean;
  permissions: string[];
  dashboard_config: Record<string, unknown>;
  reports_to: { id: string; name: string; code: string } | null;
}

export interface OrganizationalUnitSummary {
  id: string;
  name: string;
  code: string;
  unit_type: string;
}

// The full OrganizationalUnit shape (parent_id, metadata, lat/lng, etc.)
// lives in ./hierarchy.ts alongside the endpoints that return it.

export interface User {
  id: string;
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  full_name: string;
  membership_id: string;
  national_id_number: string | null;
  voter_id_number: string | null;
  date_of_birth: string | null;
  gender: string | null;
  residential_address: string | null;
  occupation: string | null;
  marital_status: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  must_change_password: boolean;
  is_active: boolean;
  is_superadmin: boolean;
  date_joined: string;
  last_login: string | null;
  role: RoleSummary | null;
  organizational_unit: OrganizationalUnitSummary | null;
  has_photo: boolean;
  photo_base64?: string | null;
  photo_content_type?: string | null;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface LoginResponse {
  user: User;
  tokens: TokenPair;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface PaginatedResponse<T> {
  count: number;
  num_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
