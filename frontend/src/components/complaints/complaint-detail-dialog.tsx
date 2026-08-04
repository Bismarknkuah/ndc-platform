"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Users } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UserPicker } from "@/components/shared/user-picker";
import * as complaintsApi from "@/lib/api/complaints";
import type { Complaint } from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

export function ComplaintDetailDialog({
  complaint,
  open,
  onOpenChange,
}: {
  complaint: Complaint | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const canManage = hasPermission(user, "hierarchy.manage") || (user?.is_superadmin ?? false);
  const [notes, setNotes] = useState("");
  const [assignee, setAssignee] = useState<{ id: string; full_name: string } | null>(null);

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof complaintsApi.updateComplaint>[1]) =>
      complaintsApi.updateComplaint(complaint!.id, payload),
    onSuccess: () => {
      toast.success("Updated.");
      queryClient.invalidateQueries({ queryKey: ["complaints"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update."),
  });

  const supportMutation = useMutation({
    mutationFn: () => complaintsApi.supportPetition(complaint!.id),
    onSuccess: (result) => {
      toast.success(
        result.already_signed
          ? "You already co-signed this petition."
          : `Co-signed. ${result.supporter_count} supporters now.`,
      );
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not co-sign."),
  });

  if (!complaint) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{complaint.subject}</DialogTitle>
          <DialogDescription>
            {complaint.complaint_type} · {complaint.submitting_unit.name} →{" "}
            {complaint.target_unit.name}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3 text-sm">
          <p className="whitespace-pre-wrap">{complaint.description}</p>
          <div className="flex justify-between border-t border-border pt-3">
            <span className="text-muted-foreground">Submitted by</span>
            <span>{complaint.submitted_by.full_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <Badge variant={complaint.status === "RESOLVED" ? "success" : "outline"}>
              {complaint.status.replace("_", " ")}
            </Badge>
          </div>
          {complaint.assigned_to && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Assigned to</span>
              <span>{complaint.assigned_to.full_name}</span>
            </div>
          )}
          {complaint.resolution_notes && (
            <div>
              <p className="text-xs text-muted-foreground">Resolution notes</p>
              <p>{complaint.resolution_notes}</p>
            </div>
          )}
        </div>

        {complaint.complaint_type === "PETITION" && (
          <Button
            variant="outline"
            onClick={() => supportMutation.mutate()}
            disabled={supportMutation.isPending}
          >
            <Users className="size-4" /> Co-sign this petition
          </Button>
        )}

        {canManage && complaint.status !== "RESOLVED" && complaint.status !== "DISMISSED" && (
          <div className="flex flex-col gap-3 border-t border-border pt-3">
            <div className="flex flex-col gap-1.5">
              <Label>Assign to (optional)</Label>
              <UserPicker value={assignee} onChange={setAssignee} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Resolution notes (optional)</Label>
              <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>
        )}

        {canManage && complaint.status !== "RESOLVED" && complaint.status !== "DISMISSED" && (
          <DialogFooter>
            {assignee && (
              <Button
                variant="outline"
                onClick={() => updateMutation.mutate({ assigned_to_id: assignee.id })}
                disabled={updateMutation.isPending}
              >
                Assign
              </Button>
            )}
            <Button
              variant="ghost"
              className="text-destructive hover:text-destructive"
              onClick={() =>
                updateMutation.mutate({ status: "DISMISSED", resolution_notes: notes })
              }
              disabled={updateMutation.isPending}
            >
              Dismiss
            </Button>
            <Button
              onClick={() =>
                updateMutation.mutate({ status: "RESOLVED", resolution_notes: notes })
              }
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Mark Resolved
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
