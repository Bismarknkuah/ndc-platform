"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { HeartHandshake, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { UnitPicker } from "@/components/shared/unit-picker";
import { SubmitWelfareDialog } from "@/components/welfare/submit-welfare-dialog";
import * as welfareApi from "@/lib/api/welfare";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasAnyPermission } from "@/lib/permissions";

const STATUS_VARIANT: Record<string, "success" | "warning" | "outline" | "destructive"> = {
  DISBURSED: "success",
  APPROVED: "success",
  UNDER_REVIEW: "warning",
  SUBMITTED: "outline",
  REJECTED: "destructive",
};

const NEXT_STATUS: Record<string, { label: string; status: string }[]> = {
  SUBMITTED: [
    { label: "Start Review", status: "UNDER_REVIEW" },
    { label: "Reject", status: "REJECTED" },
  ],
  UNDER_REVIEW: [
    { label: "Approve", status: "APPROVED" },
    { label: "Reject", status: "REJECTED" },
  ],
  APPROVED: [{ label: "Mark Disbursed", status: "DISBURSED" }],
};

export default function WelfarePage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const canReview = hasAnyPermission(user, ["finance.manage", "hierarchy.manage"]);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [jurisdictionUnit, setJurisdictionUnit] = useState<{ id: string; name: string } | null>(
    null,
  );

  const { data, isLoading } = useQuery({
    queryKey: ["welfare-requests", jurisdictionUnit?.id],
    queryFn: () =>
      welfareApi.listWelfareRequests(
        jurisdictionUnit ? { organizational_unit_id: jurisdictionUnit.id } : undefined,
      ),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      welfareApi.updateWelfareRequestStatus(
        id,
        status as "UNDER_REVIEW" | "APPROVED" | "REJECTED" | "DISBURSED",
      ),
    onSuccess: () => {
      toast.success("Request updated.");
      queryClient.invalidateQueries({ queryKey: ["welfare-requests"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update request."),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-semibold">Welfare</h1>
          <p className="text-sm text-muted-foreground">
            {jurisdictionUnit
              ? `Requests within ${jurisdictionUnit.name}`
              : "Your welfare support requests"}
          </p>
        </div>
        <div className="flex items-end gap-3">
          {canReview && (
            <div className="flex flex-col gap-1.5">
              <span className="text-xs text-muted-foreground">View jurisdiction (optional)</span>
              <div className="w-56">
                <UnitPicker
                  value={jurisdictionUnit}
                  onChange={setJurisdictionUnit}
                  placeholder="My requests only"
                />
              </div>
            </div>
          )}
          <Button onClick={() => setSubmitOpen(true)}>
            <Plus /> Request Support
          </Button>
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={HeartHandshake} title="No welfare requests" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((request) => (
            <Card key={request.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{request.category}</p>
                      <Badge variant={STATUS_VARIANT[request.status] ?? "outline"}>
                        {request.status.replace("_", " ")}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{request.description}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {request.requester.full_name} · GHS{" "}
                      {Number(request.amount_requested).toLocaleString()} ·{" "}
                      {format(new Date(request.created_at), "MMM d, yyyy")}
                    </p>
                  </div>
                  {canReview && NEXT_STATUS[request.status] && (
                    <div className="flex shrink-0 gap-1.5">
                      {NEXT_STATUS[request.status].map((action) => (
                        <Button
                          key={action.status}
                          size="sm"
                          variant={action.status === "REJECTED" ? "ghost" : "outline"}
                          className={
                            action.status === "REJECTED"
                              ? "text-destructive hover:text-destructive"
                              : undefined
                          }
                          onClick={() =>
                            statusMutation.mutate({ id: request.id, status: action.status })
                          }
                          disabled={statusMutation.isPending}
                        >
                          {action.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <SubmitWelfareDialog open={submitOpen} onOpenChange={setSubmitOpen} />
    </div>
  );
}
