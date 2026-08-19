"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ErrorState } from "@/components/shared/error-state";
import * as disciplineApi from "@/lib/api/discipline";
import { DISCIPLINARY_MEASURE_CHOICES } from "@/lib/api/discipline";
import { ApiError } from "@/lib/api/client";

const MEASURE_LABELS: Record<string, string> = {
  EXPULSION: "Expulsion",
  SUSPENSION: "Suspension for a specific period",
  REMOVAL_FROM_OFFICE: "Removal from office",
  INELIGIBILITY: "Ineligibility to hold office",
  FINE: "Fine",
  REPRIMAND: "Reprimand",
};

export default function DisciplineCaseDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [recommendation, setRecommendation] = useState("");
  const [recommendedMeasure, setRecommendedMeasure] = useState("");
  const [finalDecision, setFinalDecision] = useState("");
  const [finalMeasure, setFinalMeasure] = useState("");
  const [confirmMajority, setConfirmMajority] = useState(false);
  const [appealGrounds, setAppealGrounds] = useState("");

  const {
    data: caseData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["discipline-case", params.id],
    queryFn: () => disciplineApi.getCase(params.id),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["discipline-case", params.id] });
    queryClient.invalidateQueries({ queryKey: ["discipline-cases"] });
  };

  const conveneMutation = useMutation({
    mutationFn: () => disciplineApi.conveneCase(params.id),
    onSuccess: () => {
      toast.success("Case convened.");
      invalidate();
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not convene."),
  });

  const recommendMutation = useMutation({
    mutationFn: () => disciplineApi.recommendCase(params.id, recommendation, recommendedMeasure),
    onSuccess: () => {
      toast.success("Recommendation recorded.");
      invalidate();
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not record recommendation."),
  });

  const decideMutation = useMutation({
    mutationFn: () =>
      disciplineApi.decideCase(params.id, finalDecision, finalMeasure, confirmMajority),
    onSuccess: () => {
      toast.success("Decision recorded.");
      invalidate();
    },
    onError: (error: ApiError) => {
      if (error.code === "confirmation_required") {
        toast.error(error.message);
      } else {
        toast.error(error.message || "Could not record decision.");
      }
    },
  });

  const appealMutation = useMutation({
    mutationFn: () => disciplineApi.appealCase(params.id, appealGrounds || undefined),
    onSuccess: (appealCase) => {
      toast.success("Appeal filed at the next level up.");
      invalidate();
      router.push(`/discipline/cases/${appealCase.id}`);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not file appeal."),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (isError || !caseData) {
    return <ErrorState title="Couldn't load this case" onRetry={() => refetch()} />;
  }

  const varyingMeasure =
    finalMeasure && caseData.recommended_measure && finalMeasure !== caseData.recommended_measure;

  return (
    <div className="flex flex-col gap-6">
      <Button
        variant="ghost"
        size="sm"
        className="w-fit"
        onClick={() => router.push("/discipline")}
      >
        ← Back to Discipline
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">
            Case against {caseData.respondent.full_name}
          </h1>
          <p className="text-sm text-muted-foreground">
            {caseData.organizational_unit.name} · {caseData.grounds.replace(/_/g, " ")} · reported
            by {caseData.reported_by.full_name} on{" "}
            {format(new Date(caseData.reported_at), "MMM d, yyyy")}
          </p>
        </div>
        <Badge variant="outline">{caseData.status}</Badge>
      </div>

      <Card>
        <CardContent className="pt-6">
          <p className="text-sm">{caseData.description}</p>
        </CardContent>
      </Card>

      {caseData.convene_overdue && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertTriangle className="size-4 shrink-0" />
          Past the 14-day deadline to convene (Article 47(3)).
        </div>
      )}

      {!caseData.convened_at && caseData.status !== "APPEALED" && (
        <Card>
          <CardContent className="flex items-center justify-between pt-6">
            <div>
              <p className="font-medium">Convene the Committee</p>
              <p className="text-sm text-muted-foreground">
                Deadline: {format(new Date(caseData.convene_deadline), "MMM d, yyyy")}
              </p>
            </div>
            <Button onClick={() => conveneMutation.mutate()} disabled={conveneMutation.isPending}>
              {conveneMutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Convene
            </Button>
          </CardContent>
        </Card>
      )}

      {caseData.convened_at && !caseData.recommended_measure && (
        <Card>
          <CardContent className="flex flex-col gap-3 pt-6">
            <p className="font-medium">Record the Committee&apos;s Recommendation</p>
            <div className="flex flex-col gap-1.5">
              <Label>Recommendation</Label>
              <textarea
                value={recommendation}
                onChange={(e) => setRecommendation(e.target.value)}
                rows={3}
                className="rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Recommended measure</Label>
              <Select value={recommendedMeasure} onValueChange={setRecommendedMeasure}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select..." />
                </SelectTrigger>
                <SelectContent>
                  {DISCIPLINARY_MEASURE_CHOICES.map((m) => (
                    <SelectItem key={m} value={m}>
                      {MEASURE_LABELS[m]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              className="w-fit"
              onClick={() => recommendMutation.mutate()}
              disabled={!recommendation || !recommendedMeasure || recommendMutation.isPending}
            >
              {recommendMutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Submit Recommendation
            </Button>
          </CardContent>
        </Card>
      )}

      {caseData.recommended_measure && (
        <Card>
          <CardContent className="pt-6">
            <p className="font-medium">Committee Recommendation</p>
            <p className="mt-1 text-sm text-muted-foreground">{caseData.recommendation}</p>
            <Badge variant="secondary" className="mt-2">
              {MEASURE_LABELS[caseData.recommended_measure]}
            </Badge>
          </CardContent>
        </Card>
      )}

      {caseData.recommended_measure && !caseData.final_measure && (
        <Card>
          <CardContent className="flex flex-col gap-3 pt-6">
            <p className="font-medium">Executive Committee Decision</p>
            <div className="flex flex-col gap-1.5">
              <Label>Decision</Label>
              <textarea
                value={finalDecision}
                onChange={(e) => setFinalDecision(e.target.value)}
                rows={3}
                className="rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Final measure</Label>
              <Select value={finalMeasure} onValueChange={setFinalMeasure}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select..." />
                </SelectTrigger>
                <SelectContent>
                  {DISCIPLINARY_MEASURE_CHOICES.map((m) => (
                    <SelectItem key={m} value={m}>
                      {MEASURE_LABELS[m]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {varyingMeasure && (
              <div className="flex items-center justify-between rounded-lg border border-warning/30 bg-warning/10 p-3">
                <div>
                  <p className="text-sm font-medium">Varying the recommendation</p>
                  <p className="text-xs text-muted-foreground">
                    Article 47(9) requires a 2/3 majority of the Executive Committee to vary a
                    Disciplinary Committee recommendation. Confirm that vote has been taken.
                  </p>
                </div>
                <Switch checked={confirmMajority} onCheckedChange={setConfirmMajority} />
              </div>
            )}
            <Button
              className="w-fit"
              onClick={() => decideMutation.mutate()}
              disabled={
                !finalDecision ||
                !finalMeasure ||
                (varyingMeasure && !confirmMajority) ||
                decideMutation.isPending
              }
            >
              {decideMutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Record Decision
            </Button>
          </CardContent>
        </Card>
      )}

      {caseData.final_measure && (
        <Card>
          <CardContent className="pt-6">
            <p className="font-medium">Executive Committee Decision</p>
            <p className="mt-1 text-sm text-muted-foreground">{caseData.final_decision}</p>
            <div className="mt-2 flex items-center gap-2">
              <Badge variant="secondary">{MEASURE_LABELS[caseData.final_measure]}</Badge>
              {caseData.varied_from_recommendation && (
                <Badge variant="outline">Varied from recommendation</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {caseData.status === "DECIDED" && caseData.appeal_deadline && (
        <Card>
          <CardContent className="flex flex-col gap-3 pt-6">
            <div>
              <p className="font-medium">Appeal this decision</p>
              <p className="text-sm text-muted-foreground">
                Deadline: {format(new Date(caseData.appeal_deadline), "MMM d, yyyy")} (Article
                47(6))
              </p>
            </div>
            <Input
              placeholder="Grounds for appeal (optional)..."
              value={appealGrounds}
              onChange={(e) => setAppealGrounds(e.target.value)}
            />
            <Button
              variant="outline"
              className="w-fit"
              onClick={() => appealMutation.mutate()}
              disabled={appealMutation.isPending}
            >
              {appealMutation.isPending && <Loader2 className="size-4 animate-spin" />}
              File Appeal
            </Button>
          </CardContent>
        </Card>
      )}

      {caseData.parent_case_id && (
        <p className="text-xs text-muted-foreground">
          This case is an appeal of{" "}
          <button
            className="text-primary underline"
            onClick={() => router.push(`/discipline/cases/${caseData.parent_case_id}`)}
          >
            an earlier case
          </button>
          .
        </p>
      )}
    </div>
  );
}
