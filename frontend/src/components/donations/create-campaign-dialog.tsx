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
import * as donationsApi from "@/lib/api/donations";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  description: z.string().optional(),
  goal_amount: z.string().min(1, "Required"),
  start_date: z.string().min(1, "Required"),
  end_date: z.string().min(1, "Required"),
});
type FormValues = z.infer<typeof schema>;

export function CreateCampaignDialog({
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
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!unit) throw new ApiError("Select a target unit.", "invalid_input");
      return donationsApi.createCampaign({
        ...values,
        target_unit_id: unit.id,
        start_date: new Date(values.start_date).toISOString(),
        end_date: new Date(values.end_date).toISOString(),
      });
    },
    onSuccess: () => {
      toast.success("Campaign created.");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      reset();
      setUnit(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not create campaign."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Fundraising Campaign</DialogTitle>
          <DialogDescription>
            Set a goal, then track pledges and fulfillment against it in real time.
          </DialogDescription>
        </DialogHeader>
        <form
          id="campaign-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Title</Label>
            <Input {...register("title")} />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Goal amount (GHS)</Label>
              <Input type="number" step="0.01" min="0" {...register("goal_amount")} />
              {errors.goal_amount && (
                <p className="text-xs text-destructive">{errors.goal_amount.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Target unit</Label>
              <UnitPicker value={unit} onChange={setUnit} placeholder="Select..." />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Start date</Label>
              <Input type="datetime-local" {...register("start_date")} />
              {errors.start_date && (
                <p className="text-xs text-destructive">{errors.start_date.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>End date</Label>
              <Input type="datetime-local" {...register("end_date")} />
              {errors.end_date && (
                <p className="text-xs text-destructive">{errors.end_date.message}</p>
              )}
            </div>
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
          <Button type="submit" form="campaign-form" disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Create Campaign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
