"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Plus, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { UserPicker } from "@/components/shared/user-picker";
import * as electionsApi from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";

export function ElectorateManager({ electionId }: { electionId: string }) {
  const queryClient = useQueryClient();
  const [picking, setPicking] = useState(false);
  const [selectedUser, setSelectedUser] = useState<{ id: string; full_name: string } | null>(
    null,
  );

  const { data: voters, isLoading } = useQuery({
    queryKey: ["eligible-voters", electionId],
    queryFn: () => electionsApi.listEligibleVoters(electionId),
  });

  const addMutation = useMutation({
    mutationFn: (userId: string) => electionsApi.addEligibleVoters(electionId, [userId]),
    onSuccess: () => {
      toast.success("Voter added to the electorate - they've been notified.");
      queryClient.invalidateQueries({ queryKey: ["eligible-voters", electionId] });
      setSelectedUser(null);
      setPicking(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not add voter."),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {voters?.length ?? 0} member{voters?.length === 1 ? "" : "s"} eligible to vote
        </p>
        {picking ? (
          <div className="flex items-center gap-2">
            <div className="w-64">
              <UserPicker value={selectedUser} onChange={setSelectedUser} />
            </div>
            <Button
              size="sm"
              disabled={!selectedUser || addMutation.isPending}
              onClick={() => selectedUser && addMutation.mutate(selectedUser.id)}
            >
              {addMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
              Add
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setPicking(false)}>
              Cancel
            </Button>
          </div>
        ) : (
          <Button size="sm" onClick={() => setPicking(true)}>
            <Plus /> Add Voter
          </Button>
        )}
      </div>

      {isLoading ? null : !voters || voters.length === 0 ? (
        <EmptyState icon={UserCheck} title="No eligible voters selected yet" compact />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {voters.map((voter) => (
            <li key={voter.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <span>{voter.user.full_name}</span>
              <span className="text-xs text-muted-foreground">{voter.user.membership_id}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
