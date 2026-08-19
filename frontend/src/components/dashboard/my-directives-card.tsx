"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { ClipboardCheck, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import * as directivesApi from "@/lib/api/directives";
import { ApiError } from "@/lib/api/client";

const STATUS_VARIANT: Record<string, "success" | "warning" | "outline"> = {
  COMPLETED: "success",
  ACKNOWLEDGED: "warning",
  PENDING: "outline",
};

export function MyDirectivesCard() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["my-directives"],
    queryFn: () => directivesApi.fetchMyDirectives(),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (id: string) => directivesApi.acknowledgeDirective(id),
    onSuccess: () => {
      toast.success("Marked as acknowledged.");
      queryClient.invalidateQueries({ queryKey: ["my-directives"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update."),
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => directivesApi.completeDirective(id),
    onSuccess: () => {
      toast.success("Marked as completed.");
      queryClient.invalidateQueries({ queryKey: ["my-directives"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update."),
  });

  if (!isLoading && (!data || data.results.length === 0)) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ClipboardCheck className="size-4 text-primary" />
          Directives from Leadership
        </CardTitle>
        <CardDescription>Tasks assigned to you directly by national leadership.</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : !data || data.results.length === 0 ? (
          <EmptyState icon={ClipboardCheck} title="Nothing assigned" compact />
        ) : (
          <div className="flex flex-col gap-3">
            {data.results.map((directive) => (
              <div
                key={directive.id}
                className="flex flex-col gap-2 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium">{directive.title}</p>
                    <Badge variant={STATUS_VARIANT[directive.status] ?? "outline"}>
                      {directive.status}
                    </Badge>
                  </div>
                  {directive.description && (
                    <p className="mt-1 text-xs text-muted-foreground">{directive.description}</p>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">
                    From {directive.assigned_by.full_name}
                    {directive.due_at &&
                      ` · Due ${format(new Date(directive.due_at), "MMM d, yyyy")}`}
                  </p>
                </div>
                {directive.status === "PENDING" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => acknowledgeMutation.mutate(directive.id)}
                    disabled={acknowledgeMutation.isPending}
                  >
                    {acknowledgeMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
                    Acknowledge
                  </Button>
                )}
                {directive.status === "ACKNOWLEDGED" && (
                  <Button
                    size="sm"
                    onClick={() => completeMutation.mutate(directive.id)}
                    disabled={completeMutation.isPending}
                  >
                    {completeMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
                    Mark Complete
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
