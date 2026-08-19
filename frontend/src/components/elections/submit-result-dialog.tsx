"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UnitPicker } from "@/components/shared/unit-picker";
import { PhotoDropzone } from "@/components/elections/photo-dropzone";
import * as electionsApi from "@/lib/api/elections";
import type { Candidate } from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";

export function SubmitResultDialog({
  electionId,
  position,
  open,
  onOpenChange,
}: {
  electionId: string;
  position: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [branchUnit, setBranchUnit] = useState<{ id: string; name: string } | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [tallies, setTallies] = useState<Record<string, string>>({});
  const [photo, setPhoto] = useState<string | null>(null);
  const [registeredVoters, setRegisteredVoters] = useState("");
  const [validVotes, setValidVotes] = useState("");
  const [rejectedVotes, setRejectedVotes] = useState("");

  useEffect(() => {
    if (open) {
      electionsApi.listCandidates(electionId, position ?? undefined).then(setCandidates);
    }
  }, [open, electionId, position]);

  const mutation = useMutation({
    mutationFn: () => {
      if (!branchUnit) throw new ApiError("Select the branch (polling station).", "invalid_input");
      if (!photo) throw new ApiError("A photo of the collation sheet is required.", "invalid_input");
      return electionsApi.submitResult({
        election_id: electionId,
        branch_unit_id: branchUnit.id,
        position,
        tallies: candidates.map((c) => ({
          candidate_id: c.id,
          votes: Number(tallies[c.id] ?? 0),
        })),
        collation_sheet_photo_base64: photo,
        total_registered_voters: registeredVoters ? Number(registeredVoters) : undefined,
        total_valid_votes: validVotes ? Number(validVotes) : undefined,
        total_rejected_votes: rejectedVotes ? Number(rejectedVotes) : undefined,
      });
    },
    onSuccess: () => {
      toast.success("Result submitted.");
      queryClient.invalidateQueries({ queryKey: ["results", electionId] });
      queryClient.invalidateQueries({ queryKey: ["results-summary", electionId] });
      setBranchUnit(null);
      setTallies({});
      setPhoto(null);
      setRegisteredVoters("");
      setValidVotes("");
      setRejectedVotes("");
      onOpenChange(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not submit result."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Submit Branch Result{position ? ` (${position})` : ""}</DialogTitle>
          <DialogDescription>
            One submission per branch (polling station) per race. A photo of the physical
            result sheet is required.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label>Branch (polling station)</Label>
            <UnitPicker
              value={branchUnit}
              onChange={setBranchUnit}
              unitType="BRANCH"
              placeholder="Select your branch..."
            />
          </div>

          {candidates.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No candidates found for this race yet.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              <Label>Vote tallies</Label>
              {candidates.map((candidate) => (
                <div key={candidate.id} className="flex items-center gap-3">
                  <span className="flex-1 text-sm">
                    {candidate.name}
                    {candidate.party && (
                      <span className="ml-1.5 text-xs text-muted-foreground">
                        ({candidate.party})
                      </span>
                    )}
                  </span>
                  <Input
                    type="number"
                    min={0}
                    className="w-28"
                    value={tallies[candidate.id] ?? ""}
                    onChange={(e) =>
                      setTallies((prev) => ({ ...prev, [candidate.id]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Registered voters</Label>
              <Input
                type="number"
                min={0}
                value={registeredVoters}
                onChange={(e) => setRegisteredVoters(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Valid votes</Label>
              <Input
                type="number"
                min={0}
                value={validVotes}
                onChange={(e) => setValidVotes(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Rejected votes</Label>
              <Input
                type="number"
                min={0}
                value={rejectedVotes}
                onChange={(e) => setRejectedVotes(e.target.value)}
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Collation sheet photo (required)</Label>
            <PhotoDropzone value={photo} onChange={setPhoto} label="Photograph the result sheet..." />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!branchUnit || !photo || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Submit Result
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
