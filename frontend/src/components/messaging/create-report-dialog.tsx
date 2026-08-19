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
import * as messagingApi from "@/lib/api/messaging";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  body: z.string().min(1, "Required"),
});
type FormValues = z.infer<typeof schema>;

export function CreateReportDialog({
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
      if (!unit) throw new ApiError("Select who this report is addressed to.", "invalid_input");
      return messagingApi.createReport({ ...values, target_unit_id: unit.id });
    },
    onSuccess: () => {
      toast.success("Report submitted.");
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      reset();
      setUnit(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not submit report."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>File Upward Report</DialogTitle>
          <DialogDescription>
            Addressed to your own unit or any ancestor of it - e.g. Branch straight to
            National, or via Constituency.
          </DialogDescription>
        </DialogHeader>
        <form
          id="report-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Title</Label>
            <Input {...register("title")} />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Report</Label>
            <textarea
              {...register("body")}
              rows={5}
              className="rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {errors.body && <p className="text-xs text-destructive">{errors.body.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Addressed to</Label>
            <UnitPicker value={unit} onChange={setUnit} placeholder="Select your unit or an ancestor..." />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="report-form" disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Submit Report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
