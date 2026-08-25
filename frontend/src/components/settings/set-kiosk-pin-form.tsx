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
import * as kioskApi from "@/lib/api/kiosk";
import { ApiError } from "@/lib/api/client";

const schema = z
  .object({
    current_password: z.string().min(1, "Required"),
    pin: z.string().regex(/^\d{4,6}$/, "Must be 4 to 6 digits"),
    confirm_pin: z.string().min(1, "Required"),
  })
  .refine((data) => data.pin === data.confirm_pin, {
    message: "PINs don't match",
    path: ["confirm_pin"],
  });
type FormValues = z.infer<typeof schema>;

export function SetKioskPinForm() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      kioskApi.setKioskPin(values.current_password, values.pin),
    onSuccess: () => {
      toast.success("Kiosk Voting PIN set.");
      reset();
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not set PIN."),
  });

  return (
    <form
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="flex max-w-sm flex-col gap-4"
    >
      <p className="text-sm text-muted-foreground">
        Set a 4 to 6 digit PIN to vote in person at a registered party kiosk using just your
        membership ID and this PIN - no phone or login needed on election day. Keep it private;
        anyone with your PIN and membership ID could cast your ballot for you.
      </p>
      <div className="flex flex-col gap-1.5">
        <Label>Current password</Label>
        <Input type="password" {...register("current_password")} />
        {errors.current_password && (
          <p className="text-xs text-destructive">{errors.current_password.message}</p>
        )}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>New Kiosk PIN</Label>
        <Input type="password" inputMode="numeric" maxLength={6} {...register("pin")} />
        {errors.pin && <p className="text-xs text-destructive">{errors.pin.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Confirm PIN</Label>
        <Input type="password" inputMode="numeric" maxLength={6} {...register("confirm_pin")} />
        {errors.confirm_pin && (
          <p className="text-xs text-destructive">{errors.confirm_pin.message}</p>
        )}
      </div>
      <Button type="submit" className="w-fit" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
        Set Kiosk PIN
      </Button>
    </form>
  );
}
