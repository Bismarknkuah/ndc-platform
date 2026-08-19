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
  Download,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { UnitPicker } from "@/components/shared/unit-picker";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { EmptyState } from "@/components/shared/empty-state";
import { AssignDirectivePanel } from "@/components/dashboard/assign-directive-panel";
import * as groundIntelligenceApi from "@/lib/api/ground-intelligence";
import type { GroundIntelligence } from "@/lib/api/ground-intelligence";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasAnyPermission, hasPermission } from "@/lib/permissions";

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

function downloadReport(unitName: string, briefing: string, intelligence: GroundIntelligence) {
  const timestamp = new Date().toISOString().slice(0, 10);
  const lines = [
    `NDC Ground Intelligence Report`,
    `Location: ${unitName}`,
    `Generated: ${new Date().toLocaleString()}`,
    "",
    "=== Summary Counts ===",
    `Pending complaints: ${intelligence.counts.pending_complaints}`,
    `Welfare requests: ${intelligence.counts.pending_welfare_requests}`,
    `Discipline cases: ${intelligence.counts.pending_discipline_cases}`,
    `Total reports: ${intelligence.counts.total_reports}`,
    "",
    "=== AI Ground Briefing ===",
    briefing,
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `ground-briefing-${unitName.toLowerCase().replace(/\s+/g, "-")}-${timestamp}.txt`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function downloadText(filenamePrefix: string, unitName: string, content: string) {
  const timestamp = new Date().toISOString().slice(0, 10);
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filenamePrefix}-${unitName.toLowerCase().replace(/\s+/g, "-")}-${timestamp}.txt`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function GroundIntelligencePanel() {
  const user = useAuthStore((s) => s.user);
  const isTopTier = hasPermission(user, "analytics.ground_intelligence");
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [briefing, setBriefing] = useState<string | null>(null);
  const [officialReport, setOfficialReport] = useState<string | null>(null);
  const [speech, setSpeech] = useState<string | null>(null);
  const [speechStyle, setSpeechStyle] = useState("");

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

  const officialReportMutation = useMutation({
    mutationFn: (includeNames: boolean) =>
      groundIntelligenceApi.fetchOfficialReport(unit!.id, includeNames),
    onSuccess: (result) => setOfficialReport(result.report),
    onError: (error: ApiError) =>
      toast.error(error.message || "Could not generate the official report."),
  });

  const speechMutation = useMutation({
    mutationFn: () => groundIntelligenceApi.fetchSpeech(unit!.id, speechStyle),
    onSuccess: (result) => setSpeech(result.speech),
    onError: (error: ApiError) => toast.error(error.message || "Could not generate the speech."),
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

          {briefing && intelligence && (
            <Card className="border-primary/20 bg-primary/[0.03]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm">Briefing for {unit.name}</CardTitle>
                <div className="flex gap-1">
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
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      downloadReport(unit.name, briefing, intelligence);
                      toast.success("Report downloaded.");
                    }}
                  >
                    <Download className="size-3.5" /> Download
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">{briefing}</div>
              </CardContent>
            </Card>
          )}

          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <p className="text-sm font-medium">Official Report</p>
            <p className="text-xs text-muted-foreground">
              Two separate reports, not one with names hidden after the fact: the anonymous
              version never sends reporter identity to the AI at all. Names-included requires
              your own reveal authority and is meant for internal leadership use only.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={officialReportMutation.isPending}
                onClick={() => officialReportMutation.mutate(false)}
              >
                {officialReportMutation.isPending && (
                  <Loader2 className="size-3.5 animate-spin" />
                )}
                Generate Anonymous Report
              </Button>
              {isTopTier && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={officialReportMutation.isPending}
                  onClick={() => officialReportMutation.mutate(true)}
                >
                  {officialReportMutation.isPending && (
                    <Loader2 className="size-3.5 animate-spin" />
                  )}
                  Generate Report With Names
                </Button>
              )}
            </div>
            {officialReport && (
              <Card className="border-primary/20 bg-primary/[0.03]">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm">Official Report</CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => downloadText("official-report", unit.name, officialReport)}
                  >
                    <Download className="size-3.5" /> Download
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {officialReport}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <p className="text-sm font-medium">Generate a Speech</p>
            <p className="text-xs text-muted-foreground">
              Grounded in what was actually reported from this place. Reporter names are never
              included, regardless of style.
            </p>
            <Input
              value={speechStyle}
              onChange={(e) => setSpeechStyle(e.target.value)}
              placeholder="Style, e.g. warm and direct, or bold rally tone"
            />
            <Button
              size="sm"
              className="w-fit"
              disabled={speechMutation.isPending}
              onClick={() => speechMutation.mutate()}
            >
              {speechMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Sparkles className="size-3.5" />
              )}
              Generate Speech
            </Button>
            {speech && (
              <Card className="border-primary/20 bg-primary/[0.03]">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm">Speech Draft</CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => downloadText("speech", unit.name, speech)}
                  >
                    <Download className="size-3.5" /> Download
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">{speech}</div>
                </CardContent>
              </Card>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function LeaderDashboardPage() {
  const user = useAuthStore((s) => s.user);
  const isTopTier = hasPermission(user, "analytics.ground_intelligence");
  const canView = hasAnyPermission(user, ["analytics.ground_intelligence", "hierarchy.manage"]);

  if (!canView) {
    return (
      <ForbiddenState description="Ground Intelligence and the AI leadership tools are only available to real executives." />
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
          {isTopTier
            ? "Party-wide visibility and ground intelligence ahead of a visit."
            : "Ground intelligence within your own jurisdiction."}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MapPinned className="size-4 text-primary" />
            Ground Intelligence
          </CardTitle>
          <CardDescription>
            Real complaints, welfare requests, and reports already submitted
            {isTopTier ? " from any part of the party" : " within your own jurisdiction"}, before
            you set foot there.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GroundIntelligencePanel />
        </CardContent>
      </Card>

      {isTopTier && <AssignDirectivePanel />}
    </div>
  );
}
