"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, X } from "lucide-react";
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
import { UserPicker } from "@/components/shared/user-picker";
import * as disciplineApi from "@/lib/api/discipline";
import { ApiError } from "@/lib/api/client";

export function ElectCommitteeDialog({
  unit,
  open,
  onOpenChange,
}: {
  unit: { id: string; name: string } | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [slots, setSlots] = useState<
    [
      { id: string; full_name: string } | null,
      { id: string; full_name: string } | null,
      { id: string; full_name: string } | null,
    ]
  >([null, null, null]);

  const mutation = useMutation({
    mutationFn: () => {
      if (!unit) throw new ApiError("No unit selected.", "invalid_input");
      const ids = slots.filter((s): s is { id: string; full_name: string } => s !== null);
      return disciplineApi.electCommittee(unit.id, ids.map((s) => s.id));
    },
    onSuccess: () => {
      toast.success("Disciplinary Committee elected.");
      queryClient.invalidateQueries({ queryKey: ["discipline-committee", unit?.id] });
      setSlots([null, null, null]);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not elect committee."),
  });

  const filledCount = slots.filter(Boolean).length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Elect Disciplinary Committee</DialogTitle>
          <DialogDescription>
            Article 46(5): exactly 3 members, elected by the Executives at this level, who must
            not themselves hold an executive position here.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          {[0, 1, 2].map((index) => (
            <div key={index} className="flex items-center gap-2">
              <div className="flex-1">
                <Label className="mb-1.5 block">Member {index + 1}</Label>
                <UserPicker
                  value={slots[index]}
                  onChange={(user) => {
                    const next = [...slots] as typeof slots;
                    next[index] = user;
                    setSlots(next);
                  }}
                />
              </div>
              {slots[index] && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="mt-6"
                  onClick={() => {
                    const next = [...slots] as typeof slots;
                    next[index] = null;
                    setSlots(next);
                  }}
                >
                  <X className="size-4" />
                </Button>
              )}
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={filledCount !== 3 || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Elect Committee
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
