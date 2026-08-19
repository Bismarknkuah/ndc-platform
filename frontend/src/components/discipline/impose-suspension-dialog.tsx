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
import { UserPicker } from "@/components/shared/user-picker";
import * as disciplineApi from "@/lib/api/discipline";
import { ApiError } from "@/lib/api/client";

export function ImposeSuspensionDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<{ id: string; full_name: string } | null>(null);
  const [reason, setReason] = useState("");

  const mutation = useMutation({
    mutationFn: () => {
      if (!user) throw new ApiError("Select a member.", "invalid_input");
      return disciplineApi.imposeSuspension(user.id, reason);
    },
    onSuccess: () => {
      toast.success("Suspension imposed - must be referred to the Disciplinary Committee within one month.");
      queryClient.invalidateQueries({ queryKey: ["discipline-suspensions"] });
      setUser(null);
      setReason("");
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not impose suspension."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Impose Precautionary Suspension</DialogTitle>
          <DialogDescription>
            Article 46(1): up to 6 months, before disciplinary proceedings begin, if considered
            in the Party&apos;s interest. Must be referred to the Disciplinary Committee within
            one month or it lapses.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label>Member</Label>
            <UserPicker value={user} onChange={setUser} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Reason</Label>
            <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={!user || !reason || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Impose Suspension
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
