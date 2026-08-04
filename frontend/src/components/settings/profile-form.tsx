"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { PhotoDropzone } from "@/components/elections/photo-dropzone";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import * as authApi from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import type { User } from "@/lib/api/types";

const schema = z.object({
  first_name: z.string().min(1, "Required"),
  last_name: z.string().min(1, "Required"),
  gender: z.string().optional(),
  residential_address: z.string().optional(),
  occupation: z.string().optional(),
  marital_status: z.string().optional(),
  emergency_contact_name: z.string().optional(),
  emergency_contact_phone: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function ProfileForm({ user }: { user: User }) {
  const setUser = useAuthStore((s) => s.setUser);

  const [photoBase64, setPhotoBase64] = useState<string | null>(
    user.has_photo ? (user.photo_base64 ?? null) : null,
  );

  const photoMutation = useMutation({
    mutationFn: (base64: string | null) =>
      authApi.updateMe({
        photo_base64: base64 ?? "",
        photo_content_type: "image/jpeg",
      }),
    onSuccess: (updated) => {
      setUser(updated);
      toast.success(updated.has_photo ? "Photo updated." : "Photo removed.");
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update photo."),
  });

  const handlePhotoChange = (base64: string | null) => {
    setPhotoBase64(base64);
    photoMutation.mutate(base64);
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Avatar className="size-16">
          {photoBase64 && <AvatarImage src={`data:image/jpeg;base64,${photoBase64}`} />}
          <AvatarFallback className="text-lg">
            {user.first_name[0]}
            {user.last_name[0]}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <Label className="mb-1.5 block">Profile photo</Label>
          <PhotoDropzone
            value={photoBase64}
            onChange={handlePhotoChange}
            label="Drop a photo here, or click to browse"
            maxSizeMb={2}
          />
        </div>
      </div>

      <ProfileDetailsForm user={user} />
    </div>
  );
}

function ProfileDetailsForm({ user }: { user: User }) {
  const setUser = useAuthStore((s) => s.setUser);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: user.first_name,
      last_name: user.last_name,
      gender: user.gender ?? undefined,
      residential_address: user.residential_address ?? "",
      occupation: user.occupation ?? "",
      marital_status: user.marital_status ?? undefined,
      emergency_contact_name: user.emergency_contact_name ?? "",
      emergency_contact_phone: user.emergency_contact_phone ?? "",
    },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => authApi.updateMe(values),
    onSuccess: (updated) => {
      setUser(updated);
      toast.success("Profile updated.");
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update profile."),
  });

  return (
    <form
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="flex flex-col gap-4"
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
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Marital status</Label>
          <Controller
            control={control}
            name="marital_status"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select..." />
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

      <div className="flex flex-col gap-1.5">
        <Label>Residential address</Label>
        <Input {...register("residential_address")} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label>Occupation</Label>
        <Input {...register("occupation")} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label>Emergency contact name</Label>
          <Input {...register("emergency_contact_name")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Emergency contact phone</Label>
          <Input {...register("emergency_contact_phone")} />
        </div>
      </div>

      <Button type="submit" className="w-fit" disabled={!isDirty || mutation.isPending}>
        {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
        Save changes
      </Button>
    </form>
  );
}
