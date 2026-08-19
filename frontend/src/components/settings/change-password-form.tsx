"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as authApi from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

const schema = z
  .object({
    old_password: z.string().min(1, "Required"),
    new_password: z.string().min(8, "Must be at least 8 characters"),
    confirm_password: z.string().min(1, "Required"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });
type FormValues = z.infer<typeof schema>;

export function ChangePasswordForm() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      authApi.changePassword(values.old_password, values.new_password),
    onSuccess: () => {
      toast.success("Password changed.");
      reset();
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not change password."),
  });

  return (
    <form
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="flex max-w-sm flex-col gap-4"
    >
      <div className="flex flex-col gap-1.5">
        <Label>Current password</Label>
        <Input type="password" {...register("old_password")} />
        {errors.old_password && (
          <p className="text-xs text-destructive">{errors.old_password.message}</p>
        )}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>New password</Label>
        <Input type="password" {...register("new_password")} />
        {errors.new_password && (
          <p className="text-xs text-destructive">{errors.new_password.message}</p>
        )}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Confirm new password</Label>
        <Input type="password" {...register("confirm_password")} />
        {errors.confirm_password && (
          <p className="text-xs text-destructive">{errors.confirm_password.message}</p>
        )}
      </div>
      <Button type="submit" className="w-fit" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
        Change Password
      </Button>
    </form>
  );
}
