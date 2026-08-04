"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
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
import { PhotoDropzone } from "@/components/elections/photo-dropzone";
import * as electionsApi from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  name: z.string().min(1, "Required"),
  position: z.string().optional(),
  party: z.string().optional(),
  description: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function AddCandidateDialog({
  electionId,
  open,
  onOpenChange,
}: {
  electionId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [photo, setPhoto] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      electionsApi.createCandidate(electionId, {
        ...values,
        position: values.position || null,
        party: values.party || null,
        photo_base64: photo,
      }),
    onSuccess: (candidate) => {
      toast.success(`${candidate.name} added.`);
      queryClient.invalidateQueries({ queryKey: ["candidates", electionId] });
      reset();
      setPhoto(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not add candidate."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Candidate</DialogTitle>
          <DialogDescription>
            Leave position blank for a single-race election. Set party for a multi-party
            general election race.
          </DialogDescription>
        </DialogHeader>
        <form
          id="candidate-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Name</Label>
            <Input {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Position (optional)</Label>
              <Input {...register("position")} placeholder="e.g. President, MP - Tamale" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Party (optional)</Label>
              <Input {...register("party")} placeholder="e.g. NDC" />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Description (optional)</Label>
            <Input {...register("description")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Photo (optional)</Label>
            <PhotoDropzone value={photo} onChange={setPhoto} label="Drop a candidate photo..." />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="candidate-form" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Add Candidate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
