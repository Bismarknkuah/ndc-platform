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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UserPicker } from "@/components/shared/user-picker";
import * as departmentsApi from "@/lib/api/departments";
import { POSITION_CHOICES } from "@/lib/api/departments";
import { ApiError } from "@/lib/api/client";

export function AddTeamMemberDialog({
  departmentId,
  organizationalUnitId,
  open,
  onOpenChange,
}: {
  departmentId: string;
  organizationalUnitId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<{ id: string; full_name: string } | null>(null);
  const [position, setPosition] = useState<string>("MEMBER");

  const mutation = useMutation({
    mutationFn: () => {
      if (!user) throw new ApiError("Select a member.", "invalid_input");
      return departmentsApi.createAssignment({
        user_id: user.id,
        department_id: departmentId,
        organizational_unit_id: organizationalUnitId,
        position,
      });
    },
    onSuccess: () => {
      toast.success(`${user?.full_name} added to the team.`);
      queryClient.invalidateQueries({ queryKey: ["team-dashboard"] });
      setUser(null);
      setPosition("MEMBER");
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not add team member."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Team Member</DialogTitle>
          <DialogDescription>
            Appoint someone to this department at this organizational unit.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label>Member</Label>
            <UserPicker value={user} onChange={setUser} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Position</Label>
            <Select value={position} onValueChange={setPosition}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {POSITION_CHOICES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p.replace("_", " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={!user || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Add to Team
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
