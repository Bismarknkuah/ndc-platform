"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Crown,
  Loader2,
  MapPinned,
  MessageSquareWarning,
  HeartHandshake,
  Gavel,
  FileText,
  Sparkles,
  Copy,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { UnitPicker } from "@/components/shared/unit-picker";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { EmptyState } from "@/components/shared/empty-state";
import * as groundIntelligenceApi from "@/lib/api/ground-intelligence";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

function StatChip({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
      <Icon className="size-4 text-muted-foreground" />
      <div>
        <p className="font-display text-lg font-semibold leading-none">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

function GroundIntelligencePanel() {
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [briefing, setBriefing] = useState<string | null>(null);

  const { data: intelligence, isLoading: isLoadingIntelligence } = useQuery({
    queryKey: ["ground-intelligence", unit?.id],
    queryFn: () => groundIntelligenceApi.fetchGroundIntelligence(unit!.id),
    enabled: !!unit,
  });

  const briefingMutation = useMutation({
    mutationFn: () => groundIntelligenceApi.fetchGroundBriefing(unit!.id),
    onSuccess: (result) => setBriefing(result.briefing),
    onError: (error: ApiError) =>
      toast.error(error.message || "Could not generate the ground briefing."),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium">
          Select a region, constituency, or branch
        </label>
        <UnitPicker
          value={unit}
          onChange={(newUnit) => {
            setUnit(newUnit);
            setBriefing(null);
          }}
          placeholder="Where are you visiting?"
        />
      </div>

      {!unit && (
        <EmptyState
          icon={MapPinned}
          title="Select a place to see what's happening there"
          description="Pending complaints, welfare requests, and upward reports across the whole area, rolled up in one place."
          compact
        />
      )}

      {unit && isLoadingIntelligence && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      )}

      {unit && intelligence && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatChip
              icon={MessageSquareWarning}
              label="Pending Complaints"
              value={intelligence.counts.pending_complaints}
            />
            <StatChip
              icon={HeartHandshake}
              label="Welfare Requests"
              value={intelligence.counts.pending_welfare_requests}
            />
            <StatChip
              icon={Gavel}
              label="Discipline Cases"
              value={intelligence.counts.pending_discipline_cases}
            />
            <StatChip
              icon={FileText}
              label="Total Reports"
              value={intelligence.counts.total_reports}
            />
          </div>

          <Button
            onClick={() => briefingMutation.mutate()}
            disabled={briefingMutation.isPending}
            className="w-fit"
          >
            {briefingMutation.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Sparkles className="size-4" />
            )}
            Generate Ground Briefing
          </Button>

          {briefing && (
            <Card className="border-primary/20 bg-primary/[0.03]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm">Briefing for {unit.name}</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(briefing);
                    toast.success("Copied to clipboard.");
                  }}
                >
                  <Copy className="size-3.5" /> Copy
                </Button>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">{briefing}</div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export default function LeaderDashboardPage() {
  const user = useAuthStore((s) => s.user);
  const canView = hasPermission(user, "analytics.ground_intelligence");

  if (!canView) {
    return (
      <ForbiddenState description="The Leader Dashboard is only available to the party's national leadership." />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="flex items-center gap-2 font-display text-2xl font-semibold">
          <Crown className="size-6 text-primary" />
          Leader Dashboard
        </h1>
        <p className="text-sm text-muted-foreground">
          Party-wide visibility and ground intelligence ahead of a visit.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MapPinned className="size-4 text-primary" />
            Ground Intelligence
          </CardTitle>
          <CardDescription>
            Real complaints, welfare requests, and reports already submitted from any part of
            the party, before you set foot there.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GroundIntelligencePanel />
        </CardContent>
      </Card>
    </div>
  );
}
