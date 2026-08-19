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
import { UnitPicker } from "@/components/shared/unit-picker";
import * as membersApi from "@/lib/api/members";
import { ApiError } from "@/lib/api/client";

export function TransferMemberDialog({
  memberId,
  memberName,
  open,
  onOpenChange,
}: {
  memberId: string;
  memberName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [reason, setReason] = useState("");

  const mutation = useMutation({
    mutationFn: () => {
      if (!unit) throw new ApiError("Select a destination unit.", "invalid_input");
      return membersApi.transferMember(memberId, unit.id, reason || undefined);
    },
    onSuccess: () => {
      toast.success(`${memberName} transferred to ${unit?.name}.`);
      queryClient.invalidateQueries({ queryKey: ["member", memberId] });
      queryClient.invalidateQueries({ queryKey: ["members"] });
      onOpenChange(false);
      setUnit(null);
      setReason("");
    },
    onError: (error: ApiError) => toast.error(error.message || "Transfer failed."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Transfer {memberName}</DialogTitle>
          <DialogDescription>
            Move this member to a different organizational unit. Requires authority over
            both the current and destination units.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label>Destination unit</Label>
            <UnitPicker value={unit} onChange={setUnit} placeholder="Search for a unit..." />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Reason (optional)</Label>
            <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Transfer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
