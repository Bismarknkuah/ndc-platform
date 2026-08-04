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
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TagInput } from "@/components/shared/tag-input";
import { RolePicker } from "@/components/settings/role-picker";
import * as rolesApi from "@/lib/api/roles";
import { ALL_UNIT_TYPES, unitTypeLabel } from "@/lib/api/hierarchy";
import { ApiError } from "@/lib/api/client";
import type { RoleSummary } from "@/lib/api/types";

const schema = z.object({
  name: z.string().min(1, "Required"),
  code: z.string().min(1, "Required"),
  scope: z.string().min(1, "Required"),
  is_executive: z.boolean(),
});
type FormValues = z.infer<typeof schema>;

export function RoleFormDialog({
  open,
  onOpenChange,
  editingRole,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** null = creating a new position; otherwise editing this one. */
  editingRole: RoleSummary | null;
}) {
  // Radix's Dialog.Content unmounts from the DOM when closed (no
  // forceMount set), so this component remounts fresh each time the
  // dialog opens - a lazy useState initializer is enough to pick up
  // whichever `editingRole` is current at that moment, no effect needed
  // to "sync" it after the fact.
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open && (
        <RoleFormDialogContent
          onOpenChange={onOpenChange}
          editingRole={editingRole}
        />
      )}
    </Dialog>
  );
}

function RoleFormDialogContent({
  onOpenChange,
  editingRole,
}: {
  onOpenChange: (open: boolean) => void;
  editingRole: RoleSummary | null;
}) {
  const queryClient = useQueryClient();
  const [permissions, setPermissions] = useState<string[]>(() => editingRole?.permissions ?? []);
  const [reportsTo, setReportsTo] = useState<{ id: string; name: string } | null>(
    () => editingRole?.reports_to ?? null,
  );

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: editingRole?.name ?? "",
      code: editingRole?.code ?? "",
      scope: editingRole?.scope ?? "",
      is_executive: editingRole?.is_executive ?? true,
    },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const payload = { ...values, permissions, reports_to_id: reportsTo?.id ?? null };
      return editingRole ? rolesApi.updateRole(editingRole.id, payload) : rolesApi.createRole(payload);
    },
    onSuccess: (role) => {
      toast.success(`${role.name} ${editingRole ? "updated" : "created"}.`);
      queryClient.invalidateQueries({ queryKey: ["roles"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not save position."),
  });

  return (
    <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>{editingRole ? `Edit ${editingRole.name}` : "New Position"}</DialogTitle>
        <DialogDescription>
          {editingRole
            ? "Rename, redefine permissions, or change the reporting line - takes effect immediately, no deployment needed."
            : "Create a new party position - a Deputy role, or an office for a wing/committee not yet modeled."}
        </DialogDescription>
      </DialogHeader>
      <form
        id="role-form"
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        className="flex flex-col gap-4"
      >
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Name</Label>
            <Input {...register("name")} placeholder="e.g. Deputy Communications Director" />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Code</Label>
            <Input {...register("code")} placeholder="unique_code" />
            {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Scope (organizational level)</Label>
          <Controller
            control={control}
            name="scope"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a level..." />
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
          {errors.scope && <p className="text-xs text-destructive">{errors.scope.message}</p>}
        </div>

        <div className="flex items-center justify-between rounded-lg border border-border p-3">
          <div>
            <Label>Executive position</Label>
            <p className="text-xs text-muted-foreground">
              Executive positions appear in leadership listings and org charts.
            </p>
          </div>
          <Controller
            control={control}
            name="is_executive"
            render={({ field }) => <Switch checked={field.value} onCheckedChange={field.onChange} />}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Reports to</Label>
          <RolePicker value={reportsTo} onChange={setReportsTo} excludeId={editingRole?.id} />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Permissions</Label>
          <TagInput
            value={permissions}
            onChange={setPermissions}
            placeholder="e.g. hierarchy.manage - press Enter to add"
          />
        </div>
      </form>
      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button type="submit" form="role-form" disabled={mutation.isPending}>
          {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
          {editingRole ? "Save Changes" : "Create Position"}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}
