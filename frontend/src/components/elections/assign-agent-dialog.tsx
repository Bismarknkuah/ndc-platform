"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UnitPicker } from "@/components/shared/unit-picker";
import { UserPicker } from "@/components/shared/user-picker";
import * as electionsApi from "@/lib/api/elections";
import { POLLING_AGENT_ROLE_CHOICES } from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  role: z.string().min(1, "Required"),
  notes: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

const ROLE_LABELS: Record<string, string> = {
  PARTY_AGENT: "Party Agent",
  PRESIDING_OFFICER_LIAISON: "Presiding Officer Liaison",
  OBSERVER: "Observer",
};

export function AssignAgentDialog({
  electionId,
  open,
  onOpenChange,
}: {
  electionId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [branchUnit, setBranchUnit] = useState<{ id: string; name: string } | null>(null);
  const [agent, setAgent] = useState<{ id: string; full_name: string } | null>(null);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!branchUnit) throw new ApiError("Select a branch.", "invalid_input");
      if (!agent) throw new ApiError("Select an agent.", "invalid_input");
      return electionsApi.assignPollingAgent({
        election_id: electionId,
        branch_unit_id: branchUnit.id,
        agent_id: agent.id,
        role: values.role,
        notes: values.notes,
      });
    },
    onSuccess: () => {
      toast.success("Polling agent assigned.");
      queryClient.invalidateQueries({ queryKey: ["polling-agents", electionId] });
      reset();
      setBranchUnit(null);
      setAgent(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not assign agent."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign Polling Agent</DialogTitle>
          <DialogDescription>
            Election-day logistics: party agents, presiding officer liaisons, and observers
            at each polling station.
          </DialogDescription>
        </DialogHeader>
        <form
          id="agent-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Branch (polling station)</Label>
            <UnitPicker
              value={branchUnit}
              onChange={setBranchUnit}
              unitType="BRANCH"
              placeholder="Select a branch..."
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Agent</Label>
            <UserPicker value={agent} onChange={setAgent} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Role</Label>
            <Controller
              control={control}
              name="role"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select..." />
                  </SelectTrigger>
                  <SelectContent>
                    {POLLING_AGENT_ROLE_CHOICES.map((r) => (
                      <SelectItem key={r} value={r}>
                        {ROLE_LABELS[r]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.role && <p className="text-xs text-destructive">{errors.role.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Notes (optional)</Label>
            <Input {...register("notes")} />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="agent-form"
            disabled={!branchUnit || !agent || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Assign Agent
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
