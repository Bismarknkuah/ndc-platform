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
import { UnitPicker } from "@/components/shared/unit-picker";
import { FileDropzone, type UploadedFileInfo } from "@/components/shared/file-dropzone";
import { TagInput } from "@/components/shared/tag-input";
import * as mediaApi from "@/lib/api/media";
import { MEDIA_TYPE_CHOICES } from "@/lib/api/media";
import { ApiError } from "@/lib/api/client";

const schema = z.object({
  title: z.string().min(1, "Required"),
  media_type: z.string().min(1, "Required"),
  description: z.string().optional(),
  external_url: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function UploadMediaDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [file, setFile] = useState<UploadedFileInfo | null>(null);
  const [tags, setTags] = useState<string[]>([]);

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
      if (!file && !values.external_url) {
        throw new ApiError("Attach a file or provide an external URL.", "invalid_input");
      }
      return mediaApi.uploadMedia({
        ...values,
        tags,
        organizational_unit_id: unit.id,
        file_base64: file?.base64,
        external_url: values.external_url || undefined,
      });
    },
    onSuccess: () => {
      toast.success("Media uploaded.");
      queryClient.invalidateQueries({ queryKey: ["media"] });
      reset();
      setUnit(null);
      setFile(null);
      setTags([]);
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not upload media."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Media</DialogTitle>
          <DialogDescription>
            Small files upload directly (max ~5MB); use an external URL for larger video.
          </DialogDescription>
        </DialogHeader>
        <form
          id="media-form"
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
              <Label>Type</Label>
              <Controller
                control={control}
                name="media_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select..." />
                    </SelectTrigger>
                    <SelectContent>
                      {MEDIA_TYPE_CHOICES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t.replace("_", " ")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.media_type && (
                <p className="text-xs text-destructive">{errors.media_type.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Organizational unit</Label>
              <UnitPicker value={unit} onChange={setUnit} placeholder="Select..." />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>File (for small media)</Label>
            <FileDropzone value={file} onChange={setFile} maxSizeMb={5} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Or external URL (for large video)</Label>
            <Input {...register("external_url")} placeholder="https://..." />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Tags</Label>
            <TagInput value={tags} onChange={setTags} placeholder="e.g. rally, tamale..." />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Description (optional)</Label>
            <Input {...register("description")} />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="media-form" disabled={!unit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Upload
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
