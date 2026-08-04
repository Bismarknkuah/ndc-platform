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
import * as welfareApi from "@/lib/api/welfare";
import { WELFARE_CATEGORY_CHOICES } from "@/lib/api/welfare";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  category: z.string().min(1, "Required"),
  description: z.string().min(1, "Required"),
  amount_requested: z.string().min(1, "Required"),
});
type FormValues = z.infer<typeof schema>;

const CATEGORY_LABELS: Record<string, string> = {
  BEREAVEMENT: "Bereavement",
  MEDICAL: "Medical",
  EDUCATIONAL: "Educational",
  EMERGENCY: "Emergency",
  OTHER: "Other",
};

export function SubmitWelfareDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [document, setDocument] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      welfareApi.submitWelfareRequest({ ...values, supporting_document_base64: document }),
    onSuccess: () => {
      toast.success("Welfare request submitted.");
      queryClient.invalidateQueries({ queryKey: ["welfare-requests"] });
      reset();
      setDocument(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not submit request."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request Welfare Support</DialogTitle>
          <DialogDescription>
            Filed at your own organizational unit for review.
          </DialogDescription>
        </DialogHeader>
        <form
          id="welfare-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
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
                    {WELFARE_CATEGORY_CHOICES.map((c) => (
                      <SelectItem key={c} value={c}>
                        {CATEGORY_LABELS[c]}
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
            <Label>Amount requested (GHS)</Label>
            <Input type="number" step="0.01" min="0" {...register("amount_requested")} />
            {errors.amount_requested && (
              <p className="text-xs text-destructive">{errors.amount_requested.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Description</Label>
            <textarea
              {...register("description")}
              rows={4}
              className="rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {errors.description && (
              <p className="text-xs text-destructive">{errors.description.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Supporting document (optional)</Label>
            <PhotoDropzone value={document} onChange={setDocument} label="Attach evidence..." />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="welfare-form" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Submit Request
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
