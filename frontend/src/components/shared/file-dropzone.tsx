"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { File as FileIcon, FileUp, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { fileToBase64 } from "@/hooks/use-file-to-base64";

export interface UploadedFileInfo {
  base64: string;
  fileName: string;
  mimeType: string;
}

export function FileDropzone({
  value,
  onChange,
  label = "Drop a file here, or click to browse",
  maxSizeMb = 5,
}: {
  value: UploadedFileInfo | null;
  onChange: (file: UploadedFileInfo | null) => void;
  label?: string;
  maxSizeMb?: number;
}) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setError(null);
      const file = acceptedFiles[0];
      if (!file) return;
      if (file.size > maxSizeMb * 1024 * 1024) {
        setError(`File is too large (max ${maxSizeMb}MB).`);
        return;
      }
      const base64 = await fileToBase64(file);
      onChange({ base64, fileName: file.name, mimeType: file.type || "application/octet-stream" });
    },
    [onChange, maxSizeMb],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, maxFiles: 1 });

  if (value) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border p-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-secondary text-muted-foreground">
          <FileIcon className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{value.fileName}</p>
          <p className="text-xs text-muted-foreground">{value.mimeType}</p>
        </div>
        <button
          type="button"
          onClick={() => onChange(null)}
          className="flex size-6 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary"
        >
          <X className="size-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div>
      <div
        {...getRootProps()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-input px-6 py-8 text-center transition-colors",
          isDragActive && "border-primary bg-primary/5",
        )}
      >
        <input {...getInputProps()} />
        <FileUp className="size-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-xs text-muted-foreground/70">Max {maxSizeMb}MB</p>
      </div>
      {error && <p className="mt-1.5 text-xs text-destructive">{error}</p>}
    </div>
  );
}
