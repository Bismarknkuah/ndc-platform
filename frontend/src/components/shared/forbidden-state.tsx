import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ForbiddenState({
  description = "You don't have permission to view this page. If you believe this is a mistake, contact your organizational unit's administrator.",
}: {
  description?: string;
}) {
  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-full bg-warning/10 text-warning">
        <ShieldAlert className="size-6" />
      </div>
      <div>
        <p className="font-display text-2xl font-semibold">403 · Access denied</p>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      </div>
      <Button asChild variant="outline">
        <Link href="/dashboard">Back to Dashboard</Link>
      </Button>
    </div>
  );
}
