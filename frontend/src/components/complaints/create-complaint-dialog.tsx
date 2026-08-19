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
import * as complaintsApi from "@/lib/api/complaints";
import { COMPLAINT_TYPE_CHOICES } from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  complaint_type: z.string().min(1, "Required"),
  subject: z.string().min(1, "Required"),
  description: z.string().min(1, "Required"),
  is_anonymous: z.boolean().optional(),
});
type FormValues = z.infer<typeof schema>;

export function CreateComplaintDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [reportedUser, setReportedUser] = useState<{ id: string; full_name: string } | null>(
    null,
  );

  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const complaintType = watch("complaint_type");
  const isAccountabilityReport = complaintType === "ACCOUNTABILITY_REPORT";

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!unit) throw new ApiError("Select who this is addressed to.", "invalid_input");
      return complaintsApi.createComplaint({
        ...values,
        target_unit_id: unit.id,
        reported_user_id: reportedUser?.id,
      });
    },
    onSuccess: () => {
      toast.success("Submitted.");
      queryClient.invalidateQueries({ queryKey: ["complaints"] });
      reset();
      setUnit(null);
      setReportedUser(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not submit."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>File a Complaint or Petition</DialogTitle>
          <DialogDescription>
            A petition can gather co-signatures from other members; a complaint is
            individual.
          </DialogDescription>
        </DialogHeader>
        <form
          id="complaint-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Type</Label>
            <Controller
              control={control}
              name="complaint_type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select..." />
                  </SelectTrigger>
                  <SelectContent>
                    {COMPLAINT_TYPE_CHOICES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t === "PETITION"
                          ? "Petition (co-signable)"
                          : t === "ACCOUNTABILITY_REPORT"
                            ? "Report an Executive"
                            : "Complaint"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.complaint_type && (
              <p className="text-xs text-destructive">{errors.complaint_type.message}</p>
            )}
          </div>
          {isAccountabilityReport && (
            <div className="flex flex-col gap-1.5">
              <Label>Which executive is this about</Label>
              <UserPicker
                value={reportedUser}
                onChange={setReportedUser}
                placeholder="Search for the executive..."
              />
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <Label>Subject</Label>
            <Input {...register("subject")} />
            {errors.subject && (
              <p className="text-xs text-destructive">{errors.subject.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Description</Label>
            <textarea
              {...register("description")}
              rows={4}
              className="rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {errors.description && (
              <p className="text-xs text-destructive">{errors.description.message}</p>
            )}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              {...register("is_anonymous")}
              className="size-4 rounded border-input"
            />
            Submit anonymously
          </label>
          <p className="-mt-2 text-xs text-muted-foreground">
            Your identity is still recorded for accountability purposes, but only the party&apos;s
            national leadership can see it - everyone else, including whoever this is about,
            sees &quot;Anonymous&quot;.
          </p>
          <div className="flex flex-col gap-1.5">
            <Label>Addressed to</Label>
            <UnitPicker value={unit} onChange={setUnit} placeholder="Select your unit or an ancestor..." />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="complaint-form" disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Submit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
