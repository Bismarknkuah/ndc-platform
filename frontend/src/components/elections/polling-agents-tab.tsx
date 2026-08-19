"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { CheckCircle2, Plus, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { AssignAgentDialog } from "@/components/elections/assign-agent-dialog";
import * as electionsApi from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";

const ROLE_LABELS: Record<string, string> = {
  PARTY_AGENT: "Party Agent",
  PRESIDING_OFFICER_LIAISON: "Presiding Officer Liaison",
  OBSERVER: "Observer",
};

export function PollingAgentsTab({ electionId }: { electionId: string }) {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [assignOpen, setAssignOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["polling-agents", electionId],
    queryFn: () => electionsApi.listPollingAgents({ election_id: electionId }),
  });

  const checkInMutation = useMutation({
    mutationFn: (assignmentId: string) => electionsApi.checkInPollingAgent(assignmentId),
    onSuccess: () => {
      toast.success("Checked in.");
      queryClient.invalidateQueries({ queryKey: ["polling-agents", electionId] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not check in."),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setAssignOpen(true)}>
          <Plus /> Assign Agent
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={ShieldCheck} title="No polling agents assigned yet" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((assignment) => {
            const isSelf = assignment.agent.id === user?.id;
            return (
              <Card key={assignment.id}>
                <CardContent className="flex items-center gap-3 pt-6">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <ShieldCheck className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{assignment.agent.full_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {assignment.branch_unit.name} · {ROLE_LABELS[assignment.role]}
                      {assignment.notes ? ` · ${assignment.notes}` : ""}
                    </p>
                  </div>
                  {assignment.checked_in_at ? (
                    <Badge variant="success">
                      <CheckCircle2 className="size-3" /> Checked in{" "}
                      {format(new Date(assignment.checked_in_at), "h:mm a")}
                    </Badge>
                  ) : isSelf ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => checkInMutation.mutate(assignment.id)}
                      disabled={checkInMutation.isPending}
                    >
                      Check In
                    </Button>
                  ) : (
                    <Badge variant="outline">Not checked in</Badge>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <AssignAgentDialog electionId={electionId} open={assignOpen} onOpenChange={setAssignOpen} />
    </div>
  );
}
