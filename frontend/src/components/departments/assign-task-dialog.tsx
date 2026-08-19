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
import { UserPicker } from "@/components/shared/user-picker";
import * as departmentsApi from "@/lib/api/departments";
import { ENGAGEMENT_TYPE_CHOICES } from "@/lib/api/departments";
import { ApiError } from "@/lib/api/client";
import type { TeamRosterMember } from "@/lib/api/departments";

const schema = z.object({
  title: z.string().min(1, "Required"),
  engagement_type: z.string().min(1, "Required"),
  platform_name: z.string().optional(),
  location: z.string().optional(),
  scheduled_at: z.string().min(1, "Required"),
  description: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function AssignTaskDialog({
  departmentId,
  roster,
  open,
  onOpenChange,
}: {
  departmentId: string;
  roster: TeamRosterMember[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [assignee, setAssignee] = useState<{ id: string; full_name: string } | null>(null);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!assignee) throw new ApiError("Select a team member.", "invalid_input");
      return departmentsApi.createTask({
        ...values,
        department_id: departmentId,
        assigned_to_id: assignee.id,
        scheduled_at: new Date(values.scheduled_at).toISOString(),
      });
    },
    onSuccess: () => {
      toast.success("Task assigned.");
      queryClient.invalidateQueries({ queryKey: ["team-dashboard"] });
      reset();
      setAssignee(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not assign task."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign Task</DialogTitle>
          <DialogDescription>
            Add a diary entry for a team member - a media engagement, an event, or any
            scheduled duty.
          </DialogDescription>
        </DialogHeader>
        <form
          id="assign-task-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Team member</Label>
            <UserPicker value={assignee} onChange={setAssignee} placeholder="Select from team..." />
            {roster.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Must be an active member of this department team.
              </p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Title</Label>
            <Input {...register("title")} placeholder="e.g. Joy FM morning show" />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Engagement type</Label>
              <Controller
                control={control}
                name="engagement_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select..." />
                    </SelectTrigger>
                    <SelectContent>
                      {ENGAGEMENT_TYPE_CHOICES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {type}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.engagement_type && (
                <p className="text-xs text-destructive">{errors.engagement_type.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Scheduled at</Label>
              <Input type="datetime-local" {...register("scheduled_at")} />
              {errors.scheduled_at && (
                <p className="text-xs text-destructive">{errors.scheduled_at.message}</p>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Platform (optional)</Label>
              <Input {...register("platform_name")} placeholder="e.g. Joy FM" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Location (optional)</Label>
              <Input {...register("location")} />
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
          <Button type="submit" form="assign-task-form" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Assign Task
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
