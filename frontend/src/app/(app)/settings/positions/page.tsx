"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import { Pencil, Plus, Shield, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { DataTable } from "@/components/shared/data-table";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { RoleFormDialog } from "@/components/settings/role-form-dialog";
import * as rolesApi from "@/lib/api/roles";
import { unitTypeLabel } from "@/lib/api/hierarchy";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";
import type { RoleSummary } from "@/lib/api/types";

export default function PositionManagementPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const canManage = hasPermission(user, "hierarchy.manage_roles") || (user?.is_superadmin ?? false);

  const [formOpen, setFormOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleSummary | null>(null);
  const [retiringRole, setRetiringRole] = useState<RoleSummary | null>(null);

  const { data: roles, isLoading } = useQuery({
    queryKey: ["roles"],
    queryFn: () => rolesApi.listRoles(),
  });

  const retireMutation = useMutation({
    mutationFn: (id: string) => rolesApi.retireRole(id),
    onSuccess: () => {
      toast.success("Position retired.");
      queryClient.invalidateQueries({ queryKey: ["roles"] });
      setRetiringRole(null);
    },
    onError: (error: ApiError) => {
      toast.error(error.message || "Could not retire position.");
      setRetiringRole(null);
    },
  });

  const columns = useMemo<ColumnDef<RoleSummary>[]>(
    () => [
      {
        header: "Position",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium">{row.original.name}</p>
            <p className="font-mono text-xs text-muted-foreground">{row.original.code}</p>
          </div>
        ),
      },
      {
        header: "Scope",
        cell: ({ row }) => <Badge variant="outline">{unitTypeLabel(row.original.scope)}</Badge>,
      },
      {
        header: "Reports to",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.reports_to?.name ?? "— (top-level)"}
          </span>
        ),
      },
      {
        header: "Permissions",
        cell: ({ row }) => (
          <div className="flex max-w-xs flex-wrap gap-1">
            {row.original.permissions.slice(0, 3).map((permission) => (
              <Badge key={permission} variant="outline" className="font-mono text-[10px]">
                {permission}
              </Badge>
            ))}
            {row.original.permissions.length > 3 && (
              <Badge variant="outline" className="text-[10px]">
                +{row.original.permissions.length - 3}
              </Badge>
            )}
          </div>
        ),
      },
      ...(canManage
        ? [
            {
              header: "",
              id: "actions",
              cell: ({ row }: { row: { original: RoleSummary } }) => (
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingRole(row.original);
                      setFormOpen(true);
                    }}
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-destructive hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      setRetiringRole(row.original);
                    }}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              ),
            } as ColumnDef<RoleSummary>,
          ]
        : []),
    ],
    [canManage],
  );

  if (!canManage && !isLoading) {
    return (
      <ForbiddenState description="Position Management requires hierarchy.manage_roles - restricted to National-level executives." />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="size-5 text-primary" />
            <h1 className="text-2xl font-display font-semibold">Position Management</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Create, rename, and reconfigure party positions - no code deployment required
          </p>
        </div>
        <Button
          onClick={() => {
            setEditingRole(null);
            setFormOpen(true);
          }}
        >
          <Plus /> New Position
        </Button>
      </div>

      <DataTable
        columns={columns}
        data={roles ?? []}
        isLoading={isLoading}
        emptyTitle="No positions yet"
        onRowClick={(role) => {
          setEditingRole(role);
          setFormOpen(true);
        }}
      />

      <RoleFormDialog open={formOpen} onOpenChange={setFormOpen} editingRole={editingRole} />

      <Dialog open={!!retiringRole} onOpenChange={(open) => !open && setRetiringRole(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Retire {retiringRole?.name}?</DialogTitle>
            <DialogDescription>
              This soft-deletes the position. It&apos;s blocked if any active member currently
              holds it - reassign them first.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRetiringRole(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => retiringRole && retireMutation.mutate(retiringRole.id)}
              disabled={retireMutation.isPending}
            >
              Retire Position
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
