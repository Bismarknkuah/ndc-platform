"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import type { OrganizationalUnitSummary } from "@/lib/api/types";

/**
 * The app's signature navigation element: the party's real constitutional
 * hierarchy (National -> Regional -> Constituency -> Branch, per Article
 * 11 of the NDC Constitution) rendered as a connected pill path, used
 * everywhere a person needs to know "where am I in the org tree" -
 * member lists, department dashboards, election scopes, finance
 * summaries. Distinct from the page Breadcrumbs (which track URL
 * structure, not the party's actual structure).
 */
export function OrgUnitPath({
  units,
  onNavigate,
  className,
}: {
  units: OrganizationalUnitSummary[];
  onNavigate?: (unit: OrganizationalUnitSummary) => void;
  className?: string;
}) {
  if (units.length === 0) return null;

  return (
    <div className={cn("flex flex-wrap items-center gap-0", className)}>
      {units.map((unit, index) => {
        const isLast = index === units.length - 1;
        const content = (
          <span
            className={cn(
              "inline-flex items-center whitespace-nowrap px-3 py-1 text-xs font-medium transition-colors",
              isLast
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground hover:bg-secondary/70",
              index === 0 && "rounded-l-full",
              isLast && "rounded-r-full",
            )}
          >
            {unit.name}
          </span>
        );

        return (
          <span key={unit.id} className="flex items-center">
            {index > 0 && <span className="h-px w-2 bg-border" aria-hidden />}
            {onNavigate && !isLast ? (
              <button type="button" onClick={() => onNavigate(unit)} className="cursor-pointer">
                {content}
              </button>
            ) : (
              content
            )}
          </span>
        );
      })}
    </div>
  );
}

/** Convenience wrapper when the path segments should be real links (e.g.
 * to /hierarchy/[id]) rather than an in-page navigation callback. */
export function OrgUnitPathLinks({
  units,
  basePath = "/hierarchy",
  className,
}: {
  units: OrganizationalUnitSummary[];
  basePath?: string;
  className?: string;
}) {
  if (units.length === 0) return null;

  return (
    <div className={cn("flex flex-wrap items-center gap-0", className)}>
      {units.map((unit, index) => {
        const isLast = index === units.length - 1;
        return (
          <span key={unit.id} className="flex items-center">
            {index > 0 && <span className="h-px w-2 bg-border" aria-hidden />}
            <Link
              href={`${basePath}/${unit.id}`}
              className={cn(
                "inline-flex items-center whitespace-nowrap px-3 py-1 text-xs font-medium transition-colors",
                isLast
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/70",
                index === 0 && "rounded-l-full",
                isLast && "rounded-r-full",
              )}
            >
              {unit.name}
            </Link>
          </span>
        );
      })}
    </div>
  );
}
