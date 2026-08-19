"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function PaginationBar({
  currentPage,
  numPages,
  count,
  onPageChange,
}: {
  currentPage: number;
  numPages: number;
  count: number;
  onPageChange: (page: number) => void;
}) {
  if (numPages <= 1) return null;

  return (
    <div className="flex items-center justify-between px-1 py-3 text-sm text-muted-foreground">
      <p>
        Page {currentPage} of {numPages} · {count} total
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon"
          className="size-8"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          <ChevronLeft className="size-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="size-8"
          disabled={currentPage >= numPages}
          onClick={() => onPageChange(currentPage + 1)}
        >
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
