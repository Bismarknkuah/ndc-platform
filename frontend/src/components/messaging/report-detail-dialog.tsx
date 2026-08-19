"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
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
import * as messagingApi from "@/lib/api/messaging";
import type { Report } from "@/lib/api/messaging";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

export function ReportDetailDialog({
  report,
  open,
  onOpenChange,
}: {
  report: Report | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [notes, setNotes] = useState("");

  const canManage =
    user?.organizational_unit &&
    report &&
    (user.is_superadmin || hasPermission(user, "hierarchy.manage"));

  const mutation = useMutation({
    mutationFn: (status: "ACKNOWLEDGED" | "RESOLVED") =>
      messagingApi.updateReportStatus(report!.id, status, notes || undefined),
    onSuccess: () => {
      toast.success("Report updated.");
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update report."),
  });

  if (!report) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{report.title}</DialogTitle>
          <DialogDescription>
            {report.submitting_unit.name} → {report.target_unit.name}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3 text-sm">
          <p className="whitespace-pre-wrap">{report.body}</p>
          <div className="flex justify-between border-t border-border pt-3">
            <span className="text-muted-foreground">Submitted by</span>
            <span>{report.submitted_by.full_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <Badge variant={report.status === "RESOLVED" ? "success" : "outline"}>
              {report.status}
            </Badge>
          </div>
          {report.resolution_notes && (
            <div>
              <p className="text-xs text-muted-foreground">Resolution notes</p>
              <p>{report.resolution_notes}</p>
            </div>
          )}
        </div>

        {canManage && report.status !== "RESOLVED" && (
          <div className="flex flex-col gap-3 border-t border-border pt-3">
            <div className="flex flex-col gap-1.5">
              <Label>Resolution notes (optional)</Label>
              <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>
        )}

        {canManage && report.status !== "RESOLVED" && (
          <DialogFooter>
            {report.status === "SUBMITTED" && (
              <Button
                variant="outline"
                onClick={() => mutation.mutate("ACKNOWLEDGED")}
                disabled={mutation.isPending}
              >
                {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
                Acknowledge
              </Button>
            )}
            <Button onClick={() => mutation.mutate("RESOLVED")} disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Mark Resolved
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
