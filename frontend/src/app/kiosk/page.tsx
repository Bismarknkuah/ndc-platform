"use client";

import { useState } from "react";
import Image from "next/image";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import * as kioskApi from "@/lib/api/kiosk";
import * as electionsApi from "@/lib/api/elections";
import { ApiError } from "@/lib/api/client";

type Step = "verify" | "ballot" | "done";

export default function KioskTerminalPage() {
  const [step, setStep] = useState<Step>("verify");
  const [kioskCode, setKioskCode] = useState("");
  const [membershipId, setMembershipId] = useState("");
  const [pin, setPin] = useState("");
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [session, setSession] = useState<kioskApi.KioskVerifyResult | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  const verifyMutation = useMutation({
    mutationFn: () => kioskApi.verifyAtKiosk(kioskCode.trim(), membershipId.trim(), pin),
    onSuccess: (result) => {
      setSession(result);
      setVerifyError(null);
      setStep("ballot");
    },
    onError: (error: ApiError) => setVerifyError(error.message || "Verification failed."),
  });

  const { data: candidates, isLoading: candidatesLoading } = useQuery({
    queryKey: ["kiosk-candidates", session?.election_id],
    queryFn: () => electionsApi.listCandidates(session!.election_id),
    enabled: !!session,
  });

  const voteMutation = useMutation({
    mutationFn: () =>
      kioskApi.castKioskVote(session!.kiosk_vote_token, selectedCandidateId!),
    onSuccess: () => setStep("done"),
    onError: (error: ApiError) => setVerifyError(error.message || "Could not record your vote."),
  });

  function resetForNextVoter() {
    setStep("verify");
    setKioskCode("");
    setMembershipId("");
    setPin("");
    setVerifyError(null);
    setSession(null);
    setSelectedCandidateId(null);
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="relative size-12">
            <Image src="/ndc-logo.png" alt="NDC" fill sizes="48px" className="object-contain" />
          </div>
          <h1 className="font-display text-xl font-semibold">Party Voting Terminal</h1>
        </div>

        {step === "verify" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Verify to Vote</CardTitle>
              <CardDescription>
                Enter your membership ID and the Kiosk PIN you set in your account - no phone
                or login needed here.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Kiosk Code</Label>
                <Input
                  value={kioskCode}
                  onChange={(e) => setKioskCode(e.target.value)}
                  placeholder="Shown at this terminal, e.g. KIOSK-A1B2C3D4"
                  autoComplete="off"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Membership ID</Label>
                <Input
                  value={membershipId}
                  onChange={(e) => setMembershipId(e.target.value)}
                  autoComplete="off"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Kiosk PIN</Label>
                <Input
                  type="password"
                  inputMode="numeric"
                  maxLength={6}
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  autoComplete="off"
                />
              </div>
              {verifyError && <p className="text-sm text-destructive">{verifyError}</p>}
              <Button
                onClick={() => verifyMutation.mutate()}
                disabled={
                  !kioskCode || !membershipId || !pin || verifyMutation.isPending
                }
              >
                {verifyMutation.isPending && <Loader2 className="size-4 animate-spin" />}
                Continue
              </Button>
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <ShieldCheck className="size-3.5 shrink-0" />
                Your vote is private. This terminal never records who you voted for against
                your identity.
              </p>
            </CardContent>
          </Card>
        )}

        {step === "ballot" && session && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{session.election_title}</CardTitle>
              <CardDescription>Welcome, {session.voter_name}. Select one candidate.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {candidatesLoading ? (
                <p className="text-sm text-muted-foreground">Loading ballot...</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {candidates?.map((candidate) => (
                    <button
                      key={candidate.id}
                      onClick={() => setSelectedCandidateId(candidate.id)}
                      className={`rounded-lg border p-4 text-left transition-colors ${
                        selectedCandidateId === candidate.id
                          ? "border-primary bg-primary/5"
                          : "hover:bg-accent"
                      }`}
                    >
                      <p className="font-medium">{candidate.name}</p>
                      {candidate.party && (
                        <p className="text-xs text-muted-foreground">{candidate.party}</p>
                      )}
                    </button>
                  ))}
                </div>
              )}
              {verifyError && <p className="text-sm text-destructive">{verifyError}</p>}
              <Button
                onClick={() => voteMutation.mutate()}
                disabled={!selectedCandidateId || voteMutation.isPending}
              >
                {voteMutation.isPending && <Loader2 className="size-4 animate-spin" />}
                Cast My Vote
              </Button>
            </CardContent>
          </Card>
        )}

        {step === "done" && (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <CheckCircle2 className="size-12 text-primary" />
              <div>
                <p className="font-display text-lg font-semibold">Your vote has been recorded</p>
                <p className="text-sm text-muted-foreground">
                  Thank you for participating. Please step aside for the next voter.
                </p>
              </div>
              <Button variant="outline" onClick={resetForNextVoter}>
                Done - Next Voter
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
