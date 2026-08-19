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
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import * as membersApi from "@/lib/api/members";
import { ApiError } from "@/lib/api/client";

export function SuspendMemberDialog({
  memberId,
  memberName,
  isCurrentlyActive,
  open,
  onOpenChange,
}: {
  memberId: string;
  memberName: string;
  isCurrentlyActive: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      membersApi.updateMember(memberId, {
        is_active: !isCurrentlyActive,
        deactivation_reason: !isCurrentlyActive ? undefined : reason || undefined,
      }),
    onSuccess: () => {
      toast.success(
        isCurrentlyActive ? `${memberName} has been suspended.` : `${memberName} reactivated.`,
      );
      queryClient.invalidateQueries({ queryKey: ["member", memberId] });
      queryClient.invalidateQueries({ queryKey: ["members"] });
      onOpenChange(false);
      setReason("");
    },
    onError: (error: ApiError) => toast.error(error.message || "Action failed."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isCurrentlyActive ? `Suspend ${memberName}?` : `Reactivate ${memberName}?`}
          </DialogTitle>
          <DialogDescription>
            {isCurrentlyActive
              ? "They will lose access to the platform until reactivated."
              : "They will regain access to the platform immediately."}
          </DialogDescription>
        </DialogHeader>
        {isCurrentlyActive && (
          <div className="flex flex-col gap-1.5">
            <Label>Reason (optional)</Label>
            <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant={isCurrentlyActive ? "destructive" : "default"}
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            {isCurrentlyActive ? "Suspend" : "Reactivate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
