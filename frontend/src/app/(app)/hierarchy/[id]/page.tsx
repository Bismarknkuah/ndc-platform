"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { MapPin, Plus, Trash2, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import { OrgUnitPathLinks } from "@/components/layout/org-unit-path";
import { CreateUnitDialog } from "@/components/hierarchy/create-unit-dialog";
import * as hierarchyApi from "@/lib/api/hierarchy";
import { unitTypeLabel } from "@/lib/api/hierarchy";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

export default function HierarchyUnitDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const canManage = hasPermission(user, "hierarchy.manage");

  const [createChildOpen, setCreateChildOpen] = useState(false);
  const [deactivateOpen, setDeactivateOpen] = useState(false);

  const {
    data: unit,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["hierarchy-unit", params.id],
    queryFn: () => hierarchyApi.getUnit(params.id),
  });

  const { data: ancestors } = useQuery({
    queryKey: ["unit-ancestors", params.id],
    queryFn: () => hierarchyApi.getUnitAncestors(params.id),
  });

  const { data: children, isLoading: childrenLoading } = useQuery({
    queryKey: ["unit-children", params.id],
    queryFn: () => hierarchyApi.listUnits({ parent_id: params.id, page: 1 }),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => hierarchyApi.deactivateUnit(params.id),
    onSuccess: () => {
      toast.success("Unit deactivated.");
      queryClient.invalidateQueries({ queryKey: ["hierarchy-units"] });
      router.push("/hierarchy");
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not deactivate unit."),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (isError || !unit) {
    return <ErrorState title="Couldn't load this unit" onRetry={() => refetch()} />;
  }

  const fullPath = [...(ancestors ?? []), unit];

  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" size="sm" className="w-fit" onClick={() => router.push("/hierarchy")}>
        ← Back to Hierarchy
      </Button>

      <OrgUnitPathLinks units={fullPath} />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-display font-semibold">{unit.name}</h1>
            <Badge variant="outline">{unitTypeLabel(unit.unit_type)}</Badge>
          </div>
          <p className="font-mono text-sm text-muted-foreground">{unit.code}</p>
        </div>

        {canManage && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setCreateChildOpen(true)}>
              <Plus /> Add Child Unit
            </Button>
            <Button variant="destructive" onClick={() => setDeactivateOpen(true)}>
              <Trash2 /> Deactivate
            </Button>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Details</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Parent</span>
              <span>{unit.parent_name ?? "— (root)"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={unit.is_active ? "success" : "destructive"}>
                {unit.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            {unit.latitude != null && (
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1 text-muted-foreground">
                  <MapPin className="size-3.5" /> Coordinates
                </span>
                <span className="font-mono text-xs">
                  {unit.latitude.toFixed(4)}, {unit.longitude?.toFixed(4)}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span>{new Date(unit.created_at).toLocaleDateString()}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">
              Child Units {children ? `(${children.count})` : ""}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {childrenLoading ? (
              <div className="p-4">
                <Skeleton className="h-24" />
              </div>
            ) : !children || children.results.length === 0 ? (
              <EmptyState
                icon={Users}
                title="No child units"
                description="This unit has no subordinate units yet."
                compact
              />
            ) : (
              <ul className="divide-y divide-border">
                {children.results.map((child) => (
                  <li key={child.id}>
                    <button
                      onClick={() => router.push(`/hierarchy/${child.id}`)}
                      className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-secondary/50"
                    >
                      <div>
                        <p className="text-sm font-medium">{child.name}</p>
                        <p className="font-mono text-xs text-muted-foreground">{child.code}</p>
                      </div>
                      <Badge variant="outline">{unitTypeLabel(child.unit_type)}</Badge>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {canManage && (
        <>
          <CreateUnitDialog
            open={createChildOpen}
            onOpenChange={setCreateChildOpen}
            parent={{ id: unit.id, name: unit.name }}
          />
          <Dialog open={deactivateOpen} onOpenChange={setDeactivateOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Deactivate {unit.name}?</DialogTitle>
                <DialogDescription>
                  This soft-deletes the unit (preserving audit history). It cannot be undone
                  from here, and units with active child units cannot be deactivated - move or
                  deactivate children first.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDeactivateOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => deactivateMutation.mutate()}
                  disabled={deactivateMutation.isPending}
                >
                  Deactivate
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </>
      )}
    </div>
  );
}
