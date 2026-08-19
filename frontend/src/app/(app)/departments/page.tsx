"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Building2, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import * as departmentsApi from "@/lib/api/departments";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission, hasAnyPermission } from "@/lib/permissions";
import { CreateDepartmentDialog } from "@/components/departments/create-department-dialog";

export default function DepartmentsPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const canCreate = hasPermission(user, "hierarchy.manage_roles") || (user?.is_superadmin ?? false);
  // Full oversight - the same "genuinely broad, not one department"
  // authority already used for the office-oversight fix and the
  // Leader Dashboard - sees every department, since that is exactly
  // what real party-wide oversight means. Everyone else sees only the
  // department(s) they are actually assigned to, not the whole
  // 14-department directory.
  const hasFullOversight =
    hasAnyPermission(user, ["hierarchy.manage", "analytics.ground_intelligence"]) ||
    (user?.is_superadmin ?? false);
  const [createOpen, setCreateOpen] = useState(false);

  const { data: allDepartments, isLoading: isLoadingAll } = useQuery({
    queryKey: ["departments"],
    queryFn: departmentsApi.listDepartments,
    enabled: hasFullOversight,
  });

  const { data: myAssignments, isLoading: isLoadingMine } = useQuery({
    queryKey: ["my-department-assignments"],
    queryFn: departmentsApi.myAssignments,
    enabled: !hasFullOversight,
  });

  const isLoading = hasFullOversight ? isLoadingAll : isLoadingMine;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Departments</h1>
          <p className="text-sm text-muted-foreground">
            {hasFullOversight
              ? "Departmental chain of command - each runs parallel to the geographic hierarchy"
              : "The department(s) you're part of"}
          </p>
        </div>
        {canCreate && (
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> New Department
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : hasFullOversight ? (
        !allDepartments || allDepartments.length === 0 ? (
          <EmptyState icon={Building2} title="No departments yet" />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {allDepartments.map((department) => (
              <Card
                key={department.id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => router.push(`/departments/${department.id}`)}
              >
                <CardContent className="flex items-start gap-3 pt-6">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Building2 className="size-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium">{department.name}</p>
                    <p className="font-mono text-xs text-muted-foreground">{department.code}</p>
                    {department.description && (
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                        {department.description}
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      ) : !myAssignments || myAssignments.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="You're not part of a department"
          description="Ask a national-level executive to add you to one, if that's expected."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {myAssignments.map((assignment) => (
            <Card
              key={assignment.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() =>
                router.push(
                  `/departments/${assignment.department.id}?unit=${assignment.organizational_unit.id}`,
                )
              }
            >
              <CardContent className="flex items-start gap-3 pt-6">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Building2 className="size-5" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{assignment.department.name}</p>
                    <Badge variant="outline">{assignment.position.replace("_", " ")}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {assignment.organizational_unit.name}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {canCreate && <CreateDepartmentDialog open={createOpen} onOpenChange={setCreateOpen} />}
    </div>
  );
}
