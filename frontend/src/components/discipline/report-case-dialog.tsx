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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UnitPicker } from "@/components/shared/unit-picker";
import { UserPicker } from "@/components/shared/user-picker";
import * as disciplineApi from "@/lib/api/discipline";
import { DISCIPLINE_GROUND_CHOICES } from "@/lib/api/discipline";
import { ApiError } from "@/lib/api/client";

const GROUND_LABELS: Record<string, string> = {
  CONSTITUTIONAL_BREACH: "Breach of the Constitution",
  ANTI_PARTY_CONDUCT: "Anti-Party conduct",
  INSUBORDINATION: "Insubordination or negligence",
  CONFIDENTIALITY_BREACH: "Unauthorised disclosure of confidential information",
  OTHER: "Other conduct adversely affecting the Party",
};

const schema = z.object({
  grounds: z.string().min(1, "Required"),
  description: z.string().min(1, "Required"),
});
type FormValues = z.infer<typeof schema>;

export function ReportCaseDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [respondent, setRespondent] = useState<{ id: string; full_name: string } | null>(null);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!unit) throw new ApiError("Select the unit this case is at.", "invalid_input");
      if (!respondent) throw new ApiError("Select who this case is against.", "invalid_input");
      return disciplineApi.reportCase({
        ...values,
        organizational_unit_id: unit.id,
        respondent_id: respondent.id,
      });
    },
    onSuccess: (createdCase) => {
      toast.success("Case reported to the Disciplinary Committee.");
      queryClient.invalidateQueries({ queryKey: ["discipline-cases"] });
      reset();
      setUnit(null);
      setRespondent(null);
      onOpenChange(false);
      router.push(`/discipline/cases/${createdCase.id}`);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not report case."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Report to the Disciplinary Committee</DialogTitle>
          <DialogDescription>
            Article 46(8) - constitutional breach, anti-Party conduct, insubordination,
            confidentiality breach, or other conduct adversely affecting the Party.
          </DialogDescription>
        </DialogHeader>
        <form
          id="report-case-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Against (member)</Label>
            <UserPicker value={respondent} onChange={setRespondent} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Unit (where the case will be heard)</Label>
            <UnitPicker value={unit} onChange={setUnit} placeholder="Select a unit..." />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Grounds</Label>
            <Controller
              control={control}
              name="grounds"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select..." />
                  </SelectTrigger>
                  <SelectContent>
                    {DISCIPLINE_GROUND_CHOICES.map((g) => (
                      <SelectItem key={g} value={g}>
                        {GROUND_LABELS[g]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.grounds && (
              <p className="text-xs text-destructive">{errors.grounds.message}</p>
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
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="report-case-form"
            disabled={!unit || !respondent || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Report Case
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
