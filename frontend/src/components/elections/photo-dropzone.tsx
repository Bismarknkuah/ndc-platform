"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { ImageUp, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { fileToBase64 } from "@/hooks/use-file-to-base64";

export function PhotoDropzone({
  value,
  onChange,
  label = "Drop a photo here, or click to browse",
  maxSizeMb = 2,
}: {
  /** Raw base64 (no data: prefix), matching the backend's convention. */
  value: string | null;
  onChange: (base64: string | null) => void;
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
      onChange(base64);
    },
    [onChange, maxSizeMb],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [] },
    maxFiles: 1,
  });

  if (value) {
    return (
      <div className="relative w-fit">
        {/* eslint-disable-next-line @next/next/no-img-element -- base64 data URI, not a static asset */}
        <img
          src={`data:image/jpeg;base64,${value}`}
          alt="Uploaded"
          className="h-32 w-auto rounded-md border border-border object-cover"
        />
        <button
          type="button"
          onClick={() => onChange(null)}
          className="absolute -top-2 -right-2 flex size-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm"
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
        <ImageUp className="size-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-xs text-muted-foreground/70">JPEG or PNG, max {maxSizeMb}MB</p>
      </div>
      {error && <p className="mt-1.5 text-xs text-destructive">{error}</p>}
    </div>
  );
}
