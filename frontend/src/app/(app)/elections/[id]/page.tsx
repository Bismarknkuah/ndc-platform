"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { Loader2, Plus, Upload, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { UnitPicker } from "@/components/shared/unit-picker";
import { AddCandidateDialog } from "@/components/elections/add-candidate-dialog";
import { SubmitResultDialog } from "@/components/elections/submit-result-dialog";
import { ResultsSummaryChart } from "@/components/elections/results-summary-chart";
import { VotingPanel } from "@/components/elections/voting-panel";
import { ElectorateManager } from "@/components/elections/electorate-manager";
import { PollingAgentsTab } from "@/components/elections/polling-agents-tab";
import { KiosksTab } from "@/components/elections/kiosks-tab";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";
import * as electionsApi from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";

const STATUS_TRANSITIONS: Record<string, string[]> = {
  DRAFT: ["OPEN", "CANCELLED"],
  OPEN: ["COLLATION", "COMPLETED", "CANCELLED"],
  COLLATION: ["COMPLETED", "CANCELLED"],
  COMPLETED: [],
  CANCELLED: [],
};

export default function ElectionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const [addCandidateOpen, setAddCandidateOpen] = useState(false);
  const [submitResultOpen, setSubmitResultOpen] = useState(false);
  const [summaryUnit, setSummaryUnit] = useState<{ id: string; name: string } | null>(null);
  const [summaryPosition, setSummaryPosition] = useState<string>("");

  const {
    data: election,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["election", params.id],
    queryFn: () => electionsApi.getElection(params.id),
  });

  const { data: candidates } = useQuery({
    queryKey: ["candidates", params.id],
    queryFn: () => electionsApi.listCandidates(params.id),
    enabled: !!election,
  });

  const effectiveSummaryUnit = summaryUnit ?? election?.scope_unit ?? null;

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["results-summary", params.id, effectiveSummaryUnit?.id, summaryPosition],
    queryFn: () =>
      electionsApi.getResultSummary(
        params.id,
        effectiveSummaryUnit!.id,
        summaryPosition || undefined,
      ),
    enabled: !!election && !!effectiveSummaryUnit,
  });

  const statusMutation = useMutation({
    mutationFn: (status: "OPEN" | "COLLATION" | "COMPLETED" | "CANCELLED") =>
      electionsApi.updateElectionStatus(params.id, status),
    onSuccess: () => {
      toast.success("Election status updated.");
      queryClient.invalidateQueries({ queryKey: ["election", params.id] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update status."),
  });

  const positions = [
    ...new Set((candidates ?? []).map((c) => c.position).filter(Boolean)),
  ] as string[];

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (isError || !election) {
    return <ErrorState title="Couldn't load this election" onRetry={() => refetch()} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" size="sm" className="w-fit" onClick={() => router.push("/elections")}>
        ← Back to Elections
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-display font-semibold">{election.title}</h1>
            <Badge variant="outline">{election.status}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {election.election_type.replace("_", " ")} · {election.scope_unit.name} ·{" "}
            {format(new Date(election.start_date), "MMM d")} –{" "}
            {format(new Date(election.end_date), "MMM d, yyyy")}
          </p>
          {election.description && (
            <p className="mt-1 text-sm text-muted-foreground">{election.description}</p>
          )}
        </div>

        {STATUS_TRANSITIONS[election.status]?.length > 0 && (
          <div className="flex gap-2">
            {STATUS_TRANSITIONS[election.status].map((nextStatus) => (
              <Button
                key={nextStatus}
                variant={nextStatus === "CANCELLED" ? "destructive" : "outline"}
                size="sm"
                onClick={() =>
                  statusMutation.mutate(
                    nextStatus as "OPEN" | "COLLATION" | "COMPLETED" | "CANCELLED",
                  )
                }
                disabled={statusMutation.isPending}
              >
                {statusMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
                Mark {nextStatus}
              </Button>
            ))}
          </div>
        )}
      </div>

      <Tabs defaultValue="candidates">
        <TabsList>
          <TabsTrigger value="candidates">Candidates</TabsTrigger>
          <TabsTrigger value="results">Results & Collation</TabsTrigger>
          <TabsTrigger value="agents">Polling Agents</TabsTrigger>
          {hasPermission(user, "elections.manage") && (
            <TabsTrigger value="kiosks">Kiosks</TabsTrigger>
          )}
          {election.election_type === "PARTY_INTERNAL" && (
            <>
              <TabsTrigger value="electorate">Electorate</TabsTrigger>
              <TabsTrigger value="vote">Vote</TabsTrigger>
            </>
          )}
        </TabsList>

        <TabsContent value="candidates">
          <div className="flex flex-col gap-4">
            <div className="flex justify-end">
              <Button onClick={() => setAddCandidateOpen(true)}>
                <Plus /> Add Candidate
              </Button>
            </div>
            {!candidates || candidates.length === 0 ? (
              <EmptyState icon={UserRound} title="No candidates added yet" />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {candidates.map((candidate) => (
                  <Card key={candidate.id}>
                    <CardContent className="flex items-center gap-3 pt-6">
                      {candidate.photo_base64 ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={`data:image/jpeg;base64,${candidate.photo_base64}`}
                          alt={candidate.name}
                          className="size-12 shrink-0 rounded-full object-cover"
                        />
                      ) : (
                        <div className="flex size-12 shrink-0 items-center justify-center rounded-full bg-secondary text-muted-foreground">
                          <UserRound className="size-5" />
                        </div>
                      )}
                      <div className="min-w-0">
                        <p className="truncate font-medium">{candidate.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {candidate.position ?? "Single race"}
                          {candidate.party && ` · ${candidate.party}`}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="results">
          <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="flex flex-wrap items-end gap-3">
                <div className="flex flex-col gap-1.5">
                  <span className="text-xs text-muted-foreground">Viewing rollup at</span>
                  <div className="w-56">
                    <UnitPicker
                      value={effectiveSummaryUnit}
                      onChange={setSummaryUnit}
                      placeholder="Select a unit..."
                    />
                  </div>
                </div>
                {positions.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs text-muted-foreground">Race</span>
                    <Select value={summaryPosition} onValueChange={setSummaryPosition}>
                      <SelectTrigger className="w-48">
                        <SelectValue placeholder="Single race" />
                      </SelectTrigger>
                      <SelectContent>
                        {positions.map((p) => (
                          <SelectItem key={p} value={p}>
                            {p}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
              <Button onClick={() => setSubmitResultOpen(true)}>
                <Upload /> Submit Branch Result
              </Button>
            </div>

            {summaryLoading ? (
              <Skeleton className="h-72" />
            ) : summary ? (
              <>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-2xl font-display font-semibold">
                        {summary.total_votes_cast.toLocaleString()}
                      </p>
                      <p className="text-xs text-muted-foreground">Total votes</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-2xl font-display font-semibold">
                        {summary.leading_candidate?.candidate_name ?? "—"}
                      </p>
                      <p className="text-xs text-muted-foreground">Leading</p>
                    </CardContent>
                  </Card>
                  {summary.mode === "BRANCH_COLLATION" ? (
                    <>
                      <Card>
                        <CardContent className="pt-6">
                          <p className="text-2xl font-display font-semibold">
                            {summary.branches_reported ?? 0}/{summary.branches_expected ?? 0}
                          </p>
                          <p className="text-xs text-muted-foreground">Branches reported</p>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="pt-6">
                          <p className="text-2xl font-display font-semibold">
                            {summary.turnout_percentage != null
                              ? `${summary.turnout_percentage}%`
                              : "—"}
                          </p>
                          <p className="text-xs text-muted-foreground">Turnout</p>
                        </CardContent>
                      </Card>
                    </>
                  ) : (
                    <>
                      <Card>
                        <CardContent className="pt-6">
                          <p className="text-2xl font-display font-semibold">
                            {summary.votes_cast_count ?? 0}/{summary.eligible_voters_count ?? 0}
                          </p>
                          <p className="text-xs text-muted-foreground">Votes cast</p>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="pt-6">
                          <p className="text-2xl font-display font-semibold">
                            {summary.turnout_percentage != null
                              ? `${summary.turnout_percentage}%`
                              : "—"}
                          </p>
                          <p className="text-xs text-muted-foreground">Turnout</p>
                        </CardContent>
                      </Card>
                    </>
                  )}
                </div>

                <ResultsSummaryChart summary={summary} />

                {summary.party_results.length > 0 && (
                  <div>
                    <p className="mb-2 text-sm font-medium">By party</p>
                    <div className="flex flex-wrap gap-2">
                      {summary.party_results.map((p) => (
                        <Badge key={p.party} variant="secondary">
                          {p.party}: {p.votes.toLocaleString()} ({p.percentage}%)
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
                Results for this election have not been published yet. They become visible to
                everyone once collation is complete.
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="agents">
          <PollingAgentsTab electionId={election.id} />
        </TabsContent>

        {hasPermission(user, "elections.manage") && (
          <TabsContent value="kiosks">
            <KiosksTab electionId={election.id} />
          </TabsContent>
        )}

        {election.election_type === "PARTY_INTERNAL" && (
          <>
            <TabsContent value="electorate">
              <ElectorateManager electionId={election.id} />
            </TabsContent>
            <TabsContent value="vote">
              <VotingPanel electionId={election.id} />
            </TabsContent>
          </>
        )}
      </Tabs>

      <AddCandidateDialog
        electionId={election.id}
        open={addCandidateOpen}
        onOpenChange={setAddCandidateOpen}
      />
      <SubmitResultDialog
        electionId={election.id}
        position={summaryPosition || null}
        open={submitResultOpen}
        onOpenChange={setSubmitResultOpen}
      />
    </div>
  );
}
