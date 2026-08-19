"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Copy, Loader2 } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { UnitPicker } from "@/components/shared/unit-picker";
import { apiClient, ApiError } from "@/lib/api/client";
import * as rolesApi from "@/lib/api/roles";
import type { User } from "@/lib/api/types";

const provisionSchema = z.object({
  email: z.string().email("Enter a valid email"),
  phone_number: z.string().min(6, "Enter a valid phone number"),
  first_name: z.string().min(1, "Required"),
  last_name: z.string().min(1, "Required"),
  gender: z.enum(["MALE", "FEMALE", "OTHER"]),
  date_of_birth: z.string().min(1, "Required"),
  national_id_number: z.string().min(1, "Ghana Card number is required"),
  voter_id_number: z.string().optional(),
  residential_address: z.string().min(1, "Required"),
  emergency_contact_name: z.string().min(1, "Required"),
  emergency_contact_phone: z.string().min(1, "Required"),
  occupation: z.string().optional(),
  marital_status: z.enum(["SINGLE", "MARRIED", "DIVORCED", "WIDOWED", "OTHER"]).optional(),
});

type ProvisionFormValues = z.infer<typeof provisionSchema>;

interface ProvisionResponse {
  user: User;
  temporary_password: string;
}

export function ProvisionMemberDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [roleId, setRoleId] = useState<string>("");
  const [result, setResult] = useState<ProvisionResponse | null>(null);

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: () => rolesApi.listRoles(),
    enabled: open,
  });

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<ProvisionFormValues>({
    resolver: zodResolver(provisionSchema),
  });

  const mutation = useMutation({
    mutationFn: async (values: ProvisionFormValues) => {
      if (!unit) throw new ApiError("Select an organizational unit.", "invalid_input");
      const { data } = await apiClient.post<ProvisionResponse>("/auth/members/", {
        ...values,
        date_of_birth: new Date(values.date_of_birth).toISOString(),
        organizational_unit_id: unit.id,
        role_id: roleId || undefined,
      });
      return data;
    },
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["members"] });
      toast.success(`${data.user.full_name} provisioned successfully.`);
    },
    onError: (error: ApiError) => {
      toast.error(error.message || "Could not provision member.");
    },
  });

  function handleClose(nextOpen: boolean) {
    if (!nextOpen) {
      reset();
      setUnit(null);
      setRoleId("");
      setResult(null);
    }
    onOpenChange(nextOpen);
  }

  function copyPassword() {
    if (result) {
      navigator.clipboard.writeText(result.temporary_password);
      toast.success("Temporary password copied.");
    }
  }

  return (
    <Sheet open={open} onOpenChange={handleClose}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Provision Member</SheetTitle>
          <SheetDescription>
            Register a member on their behalf - an assisted, in-person registration with
            full voter/membership record data.
          </SheetDescription>
        </SheetHeader>

        {result ? (
          <div className="flex flex-col gap-4 px-1">
            <div className="rounded-lg border border-success/30 bg-success/10 p-4">
              <p className="text-sm font-medium text-success">
                {result.user.full_name} was created successfully.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Membership ID: <span className="font-mono">{result.user.membership_id}</span>
              </p>
            </div>
            <div>
              <Label>One-time temporary password</Label>
              <div className="mt-1.5 flex items-center gap-2">
                <Input readOnly value={result.temporary_password} className="font-mono" />
                <Button variant="outline" size="icon" onClick={copyPassword}>
                  <Copy className="size-4" />
                </Button>
              </div>
              <p className="mt-1.5 text-xs text-muted-foreground">
                Share this with the member now - it won&apos;t be shown again. They&apos;ll be
                required to change it on first login.
              </p>
            </div>
            <Button onClick={() => handleClose(false)}>Done</Button>
          </div>
        ) : (
          <ScrollArea className="h-[calc(100dvh-140px)] px-1">
            <form
              id="provision-form"
              onSubmit={handleSubmit((values) => mutation.mutate(values))}
              className="flex flex-col gap-4 pb-4"
            >
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>First name</Label>
                  <Input {...register("first_name")} />
                  {errors.first_name && (
                    <p className="text-xs text-destructive">{errors.first_name.message}</p>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Last name</Label>
                  <Input {...register("last_name")} />
                  {errors.last_name && (
                    <p className="text-xs text-destructive">{errors.last_name.message}</p>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Email</Label>
                <Input type="email" {...register("email")} />
                {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Phone number</Label>
                  <Input {...register("phone_number")} />
                  {errors.phone_number && (
                    <p className="text-xs text-destructive">{errors.phone_number.message}</p>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Date of birth</Label>
                  <Input type="date" {...register("date_of_birth")} />
                  {errors.date_of_birth && (
                    <p className="text-xs text-destructive">{errors.date_of_birth.message}</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Gender</Label>
                  <Controller
                    control={control}
                    name="gender"
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="MALE">Male</SelectItem>
                          <SelectItem value="FEMALE">Female</SelectItem>
                          <SelectItem value="OTHER">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.gender && (
                    <p className="text-xs text-destructive">{errors.gender.message}</p>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Marital status</Label>
                  <Controller
                    control={control}
                    name="marital_status"
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Optional" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="SINGLE">Single</SelectItem>
                          <SelectItem value="MARRIED">Married</SelectItem>
                          <SelectItem value="DIVORCED">Divorced</SelectItem>
                          <SelectItem value="WIDOWED">Widowed</SelectItem>
                          <SelectItem value="OTHER">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    )}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Ghana Card number</Label>
                  <Input {...register("national_id_number")} placeholder="GHA-XXXXXXXXX-X" />
                  {errors.national_id_number && (
                    <p className="text-xs text-destructive">
                      {errors.national_id_number.message}
                    </p>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Voter ID (optional)</Label>
                  <Input {...register("voter_id_number")} />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Residential address</Label>
                <Input {...register("residential_address")} />
                {errors.residential_address && (
                  <p className="text-xs text-destructive">
                    {errors.residential_address.message}
                  </p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Occupation (optional)</Label>
                <Input {...register("occupation")} />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Emergency contact name</Label>
                  <Input {...register("emergency_contact_name")} />
                  {errors.emergency_contact_name && (
                    <p className="text-xs text-destructive">
                      {errors.emergency_contact_name.message}
                    </p>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Emergency contact phone</Label>
                  <Input {...register("emergency_contact_phone")} />
                  {errors.emergency_contact_phone && (
                    <p className="text-xs text-destructive">
                      {errors.emergency_contact_phone.message}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Organizational unit</Label>
                <UnitPicker value={unit} onChange={setUnit} placeholder="Search for a unit..." />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Role (optional)</Label>
                <Select value={roleId} onValueChange={setRoleId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Ordinary member" />
                  </SelectTrigger>
                  <SelectContent>
                    {roles?.map((role) => (
                      <SelectItem key={role.id} value={role.id}>
                        {role.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </form>
          </ScrollArea>
        )}

        {!result && (
          <div className="mt-4 flex justify-end gap-2 px-1">
            <Button variant="outline" onClick={() => handleClose(false)}>
              Cancel
            </Button>
            <Button type="submit" form="provision-form" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Provision Member
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
