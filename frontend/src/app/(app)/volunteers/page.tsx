"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { HandHeart, MapPin, Plus, UserCheck, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateOpportunityDialog } from "@/components/volunteers/create-opportunity-dialog";
import * as volunteersApi from "@/lib/api/volunteers";
import { ApiError } from "@/lib/api/client";

const STATUS_VARIANT: Record<string, "success" | "warning" | "outline" | "secondary"> = {
  OPEN: "success",
  FILLED: "secondary",
  COMPLETED: "outline",
  CANCELLED: "outline",
};

export default function VolunteersPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["volunteer-opportunities"],
    queryFn: () => volunteersApi.listOpportunities({ upcoming: true }),
  });

  const signUpMutation = useMutation({
    mutationFn: (opportunityId: string) => volunteersApi.signUp(opportunityId),
    onSuccess: () => {
      toast.success("Signed up. Thank you for volunteering.");
      queryClient.invalidateQueries({ queryKey: ["volunteer-opportunities"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not sign up."),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Volunteers</h1>
          <p className="text-sm text-muted-foreground">
            Specific opportunities the party needs help with, and who has signed up.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus /> New Opportunity
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          icon={HandHeart}
          title="No open opportunities right now"
          description="Post one to ask members and executives to sign up."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.results.map((opportunity) => {
            const isFull = opportunity.filled_count >= opportunity.needed_count;
            return (
              <Card key={opportunity.id}>
                <CardContent className="flex flex-col gap-3 pt-6">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium">{opportunity.title}</p>
                    <Badge variant={STATUS_VARIANT[opportunity.status] ?? "outline"}>
                      {opportunity.status}
                    </Badge>
                  </div>
                  {opportunity.description && (
                    <p className="text-sm text-muted-foreground">{opportunity.description}</p>
                  )}
                  <div className="flex flex-col gap-1 text-xs text-muted-foreground">
                    <span>
                      {format(new Date(opportunity.scheduled_start), "EEE, MMM d · h:mm a")}
                    </span>
                    {opportunity.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="size-3" /> {opportunity.location}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Users className="size-3" /> {opportunity.target_unit.name}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {opportunity.filled_count} / {opportunity.needed_count} filled
                    </span>
                    <Button
                      size="sm"
                      variant={isFull ? "outline" : "default"}
                      disabled={isFull || signUpMutation.isPending}
                      onClick={() => signUpMutation.mutate(opportunity.id)}
                    >
                      <UserCheck className="size-3.5" />
                      {isFull ? "Filled" : "Sign Up"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <CreateOpportunityDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
