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
import * as eventsApi from "@/lib/api/events";
import { EVENT_TYPE_CHOICES } from "@/lib/api/events";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  description: z.string().optional(),
  event_type: z.string().min(1, "Required"),
  location: z.string().optional(),
  scheduled_start: z.string().min(1, "Required"),
  scheduled_end: z.string().min(1, "Required"),
});
type FormValues = z.infer<typeof schema>;

export function CreateEventDialog({
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
      if (!unit) throw new ApiError("Select a target unit.", "invalid_input");
      return eventsApi.createEvent({
        ...values,
        target_unit_id: unit.id,
        scheduled_start: new Date(values.scheduled_start).toISOString(),
        scheduled_end: new Date(values.scheduled_end).toISOString(),
      });
    },
    onSuccess: () => {
      toast.success("Event created. The target unit's subtree has been notified.");
      queryClient.invalidateQueries({ queryKey: ["events"] });
      reset();
      setUnit(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not create event."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Event</DialogTitle>
          <DialogDescription>A rally, town hall, fundraiser, or outreach event.</DialogDescription>
        </DialogHeader>
        <form
          id="event-form"
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
                name="event_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select..." />
                    </SelectTrigger>
                    <SelectContent>
                      {EVENT_TYPE_CHOICES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t.replace("_", " ")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.event_type && (
                <p className="text-xs text-destructive">{errors.event_type.message}</p>
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
          <Button type="submit" form="event-form" disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Create Event
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
