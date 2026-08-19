"use client";

import { useEffect, useState } from "react";
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
import * as hierarchyApi from "@/lib/api/hierarchy";
import { ALL_UNIT_TYPES, unitTypeLabel, expectedParentType } from "@/lib/api/hierarchy";
import { ApiError } from "@/lib/api/client";

const unitSchema = z.object({
  name: z.string().min(1, "Required"),
  code: z.string().min(1, "Required"),
  unit_type: z.string().min(1, "Required"),
});

type UnitFormValues = z.infer<typeof unitSchema>;

export function CreateUnitDialog({
  open,
  onOpenChange,
  parent,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-filled parent if creating a child from a unit's detail page. */
  parent: { id: string; name: string } | null;
}) {
  const queryClient = useQueryClient();
  const [parentUnit, setParentUnit] = useState<{ id: string; name: string } | null>(parent);

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { errors },
  } = useForm<UnitFormValues>({ resolver: zodResolver(unitSchema) });

  const selectedType = watch("unit_type");
  const requiredParentType = selectedType ? expectedParentType(selectedType) : null;

  useEffect(() => {
    if (open) setParentUnit(parent);
  }, [open, parent]);

  const mutation = useMutation({
    mutationFn: (values: UnitFormValues) =>
      hierarchyApi.createUnit({ ...values, parent_id: parentUnit?.id ?? null }),
    onSuccess: (unit) => {
      toast.success(`${unit.name} created.`);
      queryClient.invalidateQueries({ queryKey: ["hierarchy-units"] });
      queryClient.invalidateQueries({ queryKey: ["unit-children"] });
      reset();
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not create unit."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Organizational Unit</DialogTitle>
          <DialogDescription>
            Add a new unit to the party structure - a constituency, a branch, or an
            auxiliary body.
          </DialogDescription>
        </DialogHeader>
        <form
          id="create-unit-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Unit type</Label>
            <Controller
              control={control}
              name="unit_type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a type..." />
                  </SelectTrigger>
                  <SelectContent>
                    {ALL_UNIT_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {unitTypeLabel(type)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.unit_type && (
              <p className="text-xs text-destructive">{errors.unit_type.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Name</Label>
            <Input {...register("name")} placeholder="e.g. Ayawaso West Constituency" />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Code</Label>
            <Input {...register("code")} placeholder="Unique short code" />
            {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>
              Parent unit
              {requiredParentType && (
                <span className="ml-1 font-normal text-muted-foreground">
                  (must be {unitTypeLabel(requiredParentType)})
                </span>
              )}
            </Label>
            <UnitPicker
              value={parentUnit}
              onChange={setParentUnit}
              unitType={requiredParentType ?? undefined}
              placeholder="Search for a parent unit..."
            />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="create-unit-form" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Create Unit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
