"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { Plus, Vote } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { StaggerContainer, StaggerItem } from "@/components/shared/stagger-list";
import { CreateElectionDialog } from "@/components/elections/create-election-dialog";
import * as electionsApi from "@/lib/api/elections";

const STATUS_VARIANT: Record<string, "success" | "warning" | "outline" | "secondary"> = {
  OPEN: "success",
  COLLATION: "warning",
  COMPLETED: "secondary",
  DRAFT: "outline",
  CANCELLED: "outline",
};

export default function ElectionsPage() {
  const router = useRouter();
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["elections"],
    queryFn: () => electionsApi.listElections(),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Elections & Polls</h1>
          <p className="text-sm text-muted-foreground">
            General elections, internal party elections, and polls, with real-time collation
          </p>
        </div>
        {/* can_manage_election on the backend grants authority via either
            the "elections.manage" role permission OR being HEAD of the
            Elections/IT department at any unit - client-side permission
            checks can't cheaply express that OR without duplicating the
            department-membership query, so the button is always shown
            and an unauthorized attempt gets a clear error toast from the
            real 403 response instead of being hidden speculatively. */}
        <Button onClick={() => setCreateOpen(true)}>
          <Plus /> New Election
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={Vote} title="No elections yet" />
      ) : (
        <StaggerContainer className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.results.map((election) => (
            <StaggerItem key={election.id}>
            <Card
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/elections/${election.id}`)}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent">
                    <Vote className="size-4" />
                  </div>
                  <Badge variant={STATUS_VARIANT[election.status] ?? "outline"}>
                    {election.status}
                  </Badge>
                </div>
                <p className="mt-3 font-medium">{election.title}</p>
                <p className="text-xs text-muted-foreground">{election.scope_unit.name}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {format(new Date(election.start_date), "MMM d")} –{" "}
                  {format(new Date(election.end_date), "MMM d, yyyy")}
                </p>
              </CardContent>
            </Card>
            </StaggerItem>
          ))}
        </StaggerContainer>
      )}

      <CreateElectionDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
