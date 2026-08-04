"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Building2, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import * as departmentsApi from "@/lib/api/departments";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";
import { CreateDepartmentDialog } from "@/components/departments/create-department-dialog";

export default function DepartmentsPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const canCreate = hasPermission(user, "hierarchy.manage_roles") || (user?.is_superadmin ?? false);
  const [createOpen, setCreateOpen] = useState(false);

  const { data: departments, isLoading } = useQuery({
    queryKey: ["departments"],
    queryFn: departmentsApi.listDepartments,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Departments</h1>
          <p className="text-sm text-muted-foreground">
            Departmental chain of command - each runs parallel to the geographic hierarchy
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
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : !departments || departments.length === 0 ? (
        <EmptyState icon={Building2} title="No departments yet" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {departments.map((department) => (
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
      )}

      {canCreate && <CreateDepartmentDialog open={createOpen} onOpenChange={setCreateOpen} />}
    </div>
  );
}
