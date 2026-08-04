"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Vote as VoteIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import * as electionsApi from "@/lib/api/elections";
import type { Candidate } from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";

export function VotingPanel({ electionId }: { electionId: string }) {
  const queryClient = useQueryClient();
  const [candidatesByPosition, setCandidatesByPosition] = useState<Record<string, Candidate[]>>(
    {},
  );

  const { data: eligibility, isLoading } = useQuery({
    queryKey: ["my-eligibility", electionId],
    queryFn: () => electionsApi.getMyEligibility(electionId),
  });

  useEffect(() => {
    if (eligibility?.eligible) {
      electionsApi.listCandidates(electionId).then((candidates) => {
        const grouped: Record<string, Candidate[]> = {};
        for (const candidate of candidates) {
          const key = candidate.position ?? "__single__";
          grouped[key] = [...(grouped[key] ?? []), candidate];
        }
        setCandidatesByPosition(grouped);
      });
    }
  }, [eligibility?.eligible, electionId]);

  const voteMutation = useMutation({
    mutationFn: ({ candidateId, position }: { candidateId: string; position: string | null }) =>
      electionsApi.castVote(electionId, candidateId, position),
    onSuccess: () => {
      toast.success("Vote cast successfully.");
      queryClient.invalidateQueries({ queryKey: ["my-eligibility", electionId] });
      queryClient.invalidateQueries({ queryKey: ["results-summary", electionId] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Vote failed."),
  });

  if (isLoading) return null;

  if (!eligibility?.eligible) {
    return (
      <EmptyState
        icon={VoteIcon}
        title="You're not on the electorate for this election"
        description="Only members added by the Election & IT Director can vote directly in this election."
        compact
      />
    );
  }

  if (eligibility.election_status !== "OPEN") {
    return (
      <EmptyState
        icon={VoteIcon}
        title="Voting is not currently open"
        description={`Election status: ${eligibility.election_status}`}
        compact
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {Object.entries(candidatesByPosition).map(([positionKey, candidates]) => {
        const position = positionKey === "__single__" ? null : positionKey;
        const alreadyVoted = eligibility.voted_positions.includes(position);

        return (
          <Card key={positionKey}>
            <CardContent className="pt-6">
              <div className="mb-3 flex items-center justify-between">
                <p className="font-medium">{position ?? "This race"}</p>
                {alreadyVoted && (
                  <Badge variant="success">
                    <CheckCircle2 className="size-3" /> Voted
                  </Badge>
                )}
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {candidates.map((candidate) => (
                  <Button
                    key={candidate.id}
                    variant="outline"
                    disabled={alreadyVoted || voteMutation.isPending}
                    className="h-auto justify-start py-3"
                    onClick={() => voteMutation.mutate({ candidateId: candidate.id, position })}
                  >
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{candidate.name}</span>
                      {candidate.party && (
                        <span className="text-xs text-muted-foreground">{candidate.party}</span>
                      )}
                    </div>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        );
      })}
      {Object.keys(candidatesByPosition).length === 0 && (
        <EmptyState icon={VoteIcon} title="No candidates published yet" compact />
      )}
    </div>
  );
}
