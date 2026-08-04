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
import * as messagingApi from "@/lib/api/messaging";
import { MEETING_TYPE_CHOICES } from "@/lib/api/messaging";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  description: z.string().optional(),
  meeting_type: z.string().min(1, "Required"),
  scheduled_start: z.string().min(1, "Required"),
  scheduled_end: z.string().min(1, "Required"),
});
type FormValues = z.infer<typeof schema>;

export function CreateMeetingDialog({
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
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!unit) throw new ApiError("Select an audience unit.", "invalid_input");
      return messagingApi.createMeeting({
        ...values,
        target_unit_id: unit.id,
        scheduled_start: new Date(values.scheduled_start).toISOString(),
        scheduled_end: new Date(values.scheduled_end).toISOString(),
      });
    },
    onSuccess: () => {
      toast.success("Meeting scheduled - a real video room link was generated.");
      queryClient.invalidateQueries({ queryKey: ["meetings"] });
      reset();
      setUnit(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not schedule meeting."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schedule Meeting</DialogTitle>
          <DialogDescription>
            A real video room link is generated automatically - no external account needed.
          </DialogDescription>
        </DialogHeader>
        <form
          id="meeting-form"
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
              <Label>Type</Label>
              <Controller
                control={control}
                name="meeting_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select..." />
                    </SelectTrigger>
                    <SelectContent>
                      {MEETING_TYPE_CHOICES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t === "WORKSHOP" ? "Training Workshop" : "Meeting"}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.meeting_type && (
                <p className="text-xs text-destructive">{errors.meeting_type.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Audience unit</Label>
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
            <Label>Description (optional)</Label>
            <Input {...register("description")} />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="meeting-form" disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Schedule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
