import Link from "next/link";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-full bg-secondary text-muted-foreground">
        <Compass className="size-6" />
      </div>
      <div>
        <p className="font-display text-4xl font-semibold">404</p>
        <p className="mt-1 text-sm text-muted-foreground">
          This page doesn&apos;t exist, or you followed a broken link.
        </p>
      </div>
      <Button asChild>
        <Link href="/dashboard">Back to Dashboard</Link>
      </Button>
    </div>
  );
}
