"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { ScrollText } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { PaginationBar } from "@/components/shared/pagination-bar";
import * as auditApi from "@/lib/api/audit";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export function AuditLogTab() {
  const [actionFilter, setActionFilter] = useState("");
  const [page, setPage] = useState(1);
  const debouncedAction = useDebouncedValue(actionFilter, 300);

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", debouncedAction, page],
    queryFn: () => auditApi.listAuditLogs({ action: debouncedAction || undefined, page }),
  });

  return (
    <div className="flex flex-col gap-4">
      <Input
        placeholder="Filter by action prefix (e.g. hierarchy.role)..."
        value={actionFilter}
        onChange={(e) => {
          setActionFilter(e.target.value);
          setPage(1);
        }}
        className="max-w-sm font-mono text-xs"
      />

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={ScrollText} title="No audit entries found" compact />
      ) : (
        <>
          <ul className="divide-y divide-border rounded-lg border border-border">
            {data.results.map((entry) => (
              <li key={entry.id} className="flex items-start justify-between gap-3 px-4 py-3 text-sm">
                <div className="min-w-0">
                  <p className="font-mono text-xs text-primary">{entry.action}</p>
                  <p className="text-muted-foreground">
                    {entry.actor_email}
                    {entry.actor_role ? ` (${entry.actor_role})` : ""}
                    {entry.description ? `: ${entry.description}` : ""}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {format(new Date(entry.created_at), "MMM d, h:mm a")}
                </span>
              </li>
            ))}
          </ul>
          <PaginationBar
            currentPage={data.current_page}
            numPages={data.num_pages}
            count={data.count}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
