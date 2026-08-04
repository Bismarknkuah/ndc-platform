"use client";

import { useEffect } from "react";
import { ServerCrash } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <ServerCrash className="size-6" />
      </div>
      <div>
        <p className="font-display text-2xl font-semibold">Something broke</p>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          An unexpected error occurred. Our team has been notified; try again in a moment.
        </p>
      </div>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
