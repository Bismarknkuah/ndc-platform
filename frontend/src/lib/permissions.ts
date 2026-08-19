import type { User } from "@/lib/api/types";

/**
 * Mirrors the backend's ancestor-scoped permission model
 * (apps.*.permissions across the Django project): a permission tag on
 * the user's Role, combined - where relevant - with whether their own
 * organizational unit is the same as or an ancestor of a target unit.
 * The frontend only ever *hides/shows* UI based on this; the backend is
 * still the enforcement boundary on every request.
 */
export function hasPermission(user: User | null, tag: string): boolean {
  if (!user) return false;
  if (user.is_superadmin) return true;
  return user.role?.permissions.includes(tag) ?? false;
}

export function hasAnyPermission(user: User | null, tags: string[]): boolean {
  return tags.some((tag) => hasPermission(user, tag));
}

/** Visibility check for a nav item: no requirement, a single required
 * tag, or "any of" a list of tags. */
export function canSeeNavItem(
  user: User | null,
  item: { permission?: string; anyPermissions?: string[] },
): boolean {
  if (item.permission && !hasPermission(user, item.permission)) return false;
  if (item.anyPermissions && !hasAnyPermission(user, item.anyPermissions)) return false;
  return true;
}

export function isExecutive(user: User | null): boolean {
  return user?.role?.is_executive ?? false;
}
