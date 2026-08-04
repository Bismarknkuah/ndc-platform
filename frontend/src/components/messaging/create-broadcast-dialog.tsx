"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UnitPicker } from "@/components/shared/unit-picker";
import * as messagingApi from "@/lib/api/messaging";
import { BROADCAST_KIND_CHOICES, PRIORITY_CHOICES } from "@/lib/api/messaging";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  body: z.string().min(1, "Required"),
  kind: z.string().min(1, "Required"),
  priority: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function CreateBroadcastDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [requiresAck, setRequiresAck] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { priority: "NORMAL" } });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!unit) throw new ApiError("Select a target unit.", "invalid_input");
      return messagingApi.createBroadcast({
        ...values,
        target_unit_id: unit.id,
        requires_acknowledgement: requiresAck,
      });
    },
    onSuccess: () => {
      toast.success("Broadcast issued.");
      queryClient.invalidateQueries({ queryKey: ["broadcasts"] });
      reset();
      setUnit(null);
      setRequiresAck(false);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not issue broadcast."),
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Issue Broadcast</SheetTitle>
          <SheetDescription>
            Send a directive or announcement down your chain of command - every active
            member in the target unit&apos;s subtree is notified.
          </SheetDescription>
        </SheetHeader>
        <form
          id="broadcast-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4 px-1"
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Kind</Label>
              <Controller
                control={control}
                name="kind"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select..." />
                    </SelectTrigger>
                    <SelectContent>
                      {BROADCAST_KIND_CHOICES.map((k) => (
                        <SelectItem key={k} value={k}>
                          {k === "DIRECTIVE" ? "Directive (action required)" : "Announcement"}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.kind && <p className="text-xs text-destructive">{errors.kind.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Priority</Label>
              <Controller
                control={control}
                name="priority"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PRIORITY_CHOICES.map((p) => (
                        <SelectItem key={p} value={p}>
                          {p}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Title</Label>
            <Input {...register("title")} />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Message</Label>
            <textarea
              {...register("body")}
              rows={5}
              className="rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {errors.body && <p className="text-xs text-destructive">{errors.body.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Target unit</Label>
            <UnitPicker value={unit} onChange={setUnit} placeholder="Everyone under..." />
          </div>

          <div className="flex items-center justify-between rounded-lg border border-border p-3">
            <div>
              <Label>Requires acknowledgement</Label>
              <p className="text-xs text-muted-foreground">
                Recipients must explicitly confirm they&apos;ve read it.
              </p>
            </div>
            <Switch checked={requiresAck} onCheckedChange={setRequiresAck} />
          </div>
        </form>
        <div className="mt-4 flex justify-end gap-2 px-1">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="broadcast-form" disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Issue Broadcast
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
