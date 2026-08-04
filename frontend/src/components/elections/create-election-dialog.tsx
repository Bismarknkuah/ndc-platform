"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
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
import * as electionsApi from "@/lib/api/elections";
import { ELECTION_TYPE_CHOICES } from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  description: z.string().optional(),
  election_type: z.string().min(1, "Required"),
  start_date: z.string().min(1, "Required"),
  end_date: z.string().min(1, "Required"),
});
type FormValues = z.infer<typeof schema>;

const TYPE_LABELS: Record<string, string> = {
  NATIONAL_GENERAL: "National General Election",
  PARTY_INTERNAL: "Internal Party Election",
  POLL: "Poll / Data Gathering",
  OTHER: "Other",
};

export function CreateElectionDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();
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
      if (!unit) throw new ApiError("Select a scope unit.", "invalid_input");
      return electionsApi.createElection({
        ...values,
        scope_unit_id: unit.id,
        start_date: new Date(values.start_date).toISOString(),
        end_date: new Date(values.end_date).toISOString(),
      });
    },
    onSuccess: (election) => {
      toast.success(`${election.title} created.`);
      queryClient.invalidateQueries({ queryKey: ["elections"] });
      reset();
      setUnit(null);
      onOpenChange(false);
      router.push(`/elections/${election.id}`);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not create election."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Election</DialogTitle>
          <DialogDescription>
            A national general election, an internal party election, or a lightweight poll.
          </DialogDescription>
        </DialogHeader>
        <form
          id="election-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Title</Label>
            <Input {...register("title")} placeholder="e.g. 2028 Presidential Primary" />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Type</Label>
            <Controller
              control={control}
              name="election_type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select..." />
                  </SelectTrigger>
                  <SelectContent>
                    {ELECTION_TYPE_CHOICES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {TYPE_LABELS[t]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.election_type && (
              <p className="text-xs text-destructive">{errors.election_type.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Scope</Label>
            <UnitPicker value={unit} onChange={setUnit} placeholder="Select the unit this covers..." />
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
          <Button type="submit" form="election-form" disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Create Election
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
