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
import { PhotoDropzone } from "@/components/elections/photo-dropzone";
import * as financeApi from "@/lib/api/finance";
import { RECORD_TYPE_CHOICES, COMMON_CATEGORIES } from "@/lib/api/finance";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  record_type: z.string().min(1, "Required"),
  category: z.string().min(1, "Required"),
  amount: z.string().min(1, "Required"),
  description: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function RecordFinanceDialog({
  organizationalUnitId,
  open,
  onOpenChange,
}: {
  organizationalUnitId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [receipt, setReceipt] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      financeApi.createFinanceRecord({
        ...values,
        organizational_unit_id: organizationalUnitId,
        receipt_photo_base64: receipt,
      }),
    onSuccess: () => {
      toast.success("Recorded. Pending approval.");
      queryClient.invalidateQueries({ queryKey: ["finance-records"] });
      reset();
      setReceipt(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not record entry."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record Income / Expense</DialogTitle>
          <DialogDescription>Starts PENDING - requires finance authority to approve.</DialogDescription>
        </DialogHeader>
        <form
          id="finance-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Type</Label>
              <Controller
                control={control}
                name="record_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select..." />
                    </SelectTrigger>
                    <SelectContent>
                      {RECORD_TYPE_CHOICES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.record_type && (
                <p className="text-xs text-destructive">{errors.record_type.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Amount (GHS)</Label>
              <Input type="number" step="0.01" min="0" {...register("amount")} />
              {errors.amount && (
                <p className="text-xs text-destructive">{errors.amount.message}</p>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Category</Label>
            <Controller
              control={control}
              name="category"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select..." />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_CATEGORIES.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.category && (
              <p className="text-xs text-destructive">{errors.category.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Description (optional)</Label>
            <Input {...register("description")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Receipt (optional)</Label>
            <PhotoDropzone value={receipt} onChange={setReceipt} label="Attach a receipt..." />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="finance-form" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Record Entry
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
