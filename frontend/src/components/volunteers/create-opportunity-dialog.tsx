"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
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
import { UnitPicker } from "@/components/shared/unit-picker";
import * as volunteersApi from "@/lib/api/volunteers";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  description: z.string().optional(),
  needed_count: z.coerce.number().min(1, "Must be at least 1"),
  location: z.string().optional(),
  scheduled_start: z.string().min(1, "Required"),
  scheduled_end: z.string().min(1, "Required"),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function CreateOpportunityDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormInput>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!unit) throw new ApiError("Select a target unit.", "invalid_input");
      return volunteersApi.createOpportunity({
        ...values,
        target_unit_id: unit.id,
        scheduled_start: new Date(values.scheduled_start).toISOString(),
        scheduled_end: new Date(values.scheduled_end).toISOString(),
      });
    },
    onSuccess: () => {
      toast.success("Opportunity posted. The target unit's subtree has been notified.");
      queryClient.invalidateQueries({ queryKey: ["volunteer-opportunities"] });
      reset();
      setUnit(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not post opportunity."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Volunteer Opportunity</DialogTitle>
          <DialogDescription>Post a specific need for volunteers.</DialogDescription>
        </DialogHeader>
        <form
          id="opportunity-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values as FormValues))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Title</Label>
            <Input {...register("title")} placeholder="e.g. Ushers needed for the rally" />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>How many needed</Label>
              <Input type="number" min={1} {...register("needed_count")} />
              {errors.needed_count && (
                <p className="text-xs text-destructive">{errors.needed_count.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Target unit</Label>
              <UnitPicker value={unit} onChange={setUnit} placeholder="Select..." />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Starts</Label>
              <Input type="datetime-local" {...register("scheduled_start")} />
              {errors.scheduled_start && (
                <p className="text-xs text-destructive">{errors.scheduled_start.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Ends</Label>
              <Input type="datetime-local" {...register("scheduled_end")} />
              {errors.scheduled_end && (
                <p className="text-xs text-destructive">{errors.scheduled_end.message}</p>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Location (optional)</Label>
            <Input {...register("location")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Description (optional)</Label>
            <Input {...register("description")} />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="opportunity-form" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Post Opportunity
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
