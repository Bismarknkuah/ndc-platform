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
import { UnitPicker } from "@/components/shared/unit-picker";
import { FileDropzone, type UploadedFileInfo } from "@/components/shared/file-dropzone";
import * as documentsApi from "@/lib/api/documents";
import { DOCUMENT_CATEGORY_CHOICES } from "@/lib/api/documents";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  category: z.string().min(1, "Required"),
  description: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function UploadDocumentDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [file, setFile] = useState<UploadedFileInfo | null>(null);
  const [isPublic, setIsPublic] = useState(true);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!unit) throw new ApiError("Select an organizational unit.", "invalid_input");
      if (!file) throw new ApiError("Attach a file.", "invalid_input");
      return documentsApi.uploadDocument({
        ...values,
        organizational_unit_id: unit.id,
        file_base64: file.base64,
        file_name: file.fileName,
        mime_type: file.mimeType,
        is_public_within_party: isPublic,
      });
    },
    onSuccess: () => {
      toast.success("Document uploaded.");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      reset();
      setUnit(null);
      setFile(null);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not upload document."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload Document</DialogTitle>
          <DialogDescription>Constitution, minutes, forms, policy, or reports.</DialogDescription>
        </DialogHeader>
        <form
          id="document-form"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label>Title</Label>
            <Input {...register("title")} />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
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
                      {DOCUMENT_CATEGORY_CHOICES.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c.replace("_", " ")}
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
              <Label>Organizational unit</Label>
              <UnitPicker value={unit} onChange={setUnit} placeholder="Select..." />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Description (optional)</Label>
            <Input {...register("description")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>File</Label>
            <FileDropzone value={file} onChange={setFile} maxSizeMb={5} />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border p-3">
            <div>
              <Label>Visible party-wide</Label>
              <p className="text-xs text-muted-foreground">
                Off restricts visibility to this unit&apos;s ancestor/descendant chain only.
              </p>
            </div>
            <Switch checked={isPublic} onCheckedChange={setIsPublic} />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="document-form" disabled={!unit || !file || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Upload
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
