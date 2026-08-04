"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { AlertTriangle, Gavel, Plus, ShieldAlert, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/empty-state";
import { UnitPicker } from "@/components/shared/unit-picker";
import { ReportCaseDialog } from "@/components/discipline/report-case-dialog";
import { ElectCommitteeDialog } from "@/components/discipline/elect-committee-dialog";
import { ImposeSuspensionDialog } from "@/components/discipline/impose-suspension-dialog";
import * as disciplineApi from "@/lib/api/discipline";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";

const STATUS_VARIANT: Record<
  string,
  "success" | "warning" | "outline" | "destructive" | "secondary"
> = {
  DECIDED: "success",
  RECOMMENDED: "warning",
  CONVENED: "warning",
  REPORTED: "outline",
  APPEALED: "destructive",
  CLOSED: "secondary",
};

function MyCasesTab() {
  const router = useRouter();
  const [reportOpen, setReportOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["discipline-cases", "mine"],
    queryFn: () => disciplineApi.listCases({ mine: true }),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setReportOpen(true)}>
          <Plus /> Report a Case
        </Button>
      </div>
      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={Gavel} title="No cases involving you" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((c) => (
            <Card
              key={c.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/discipline/cases/${c.id}`)}
            >
              <CardContent className="flex items-center gap-3 pt-6">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
                  <Gavel className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{c.respondent.full_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {c.organizational_unit.name} · {c.grounds.replace(/_/g, " ")} ·{" "}
                    {format(new Date(c.reported_at), "MMM d, yyyy")}
                  </p>
                </div>
                <Badge variant={STATUS_VARIANT[c.status] ?? "outline"}>{c.status}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <ReportCaseDialog open={reportOpen} onOpenChange={setReportOpen} />
    </div>
  );
}

function CommitteeTab() {
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [electOpen, setElectOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["discipline-committee", unit?.id],
    queryFn: () => disciplineApi.listCommittees(unit!.id),
    enabled: !!unit,
  });

  const committee = data?.[0];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          <span className="text-xs text-muted-foreground">Unit</span>
          <div className="w-64">
            <UnitPicker value={unit} onChange={setUnit} placeholder="Select a unit..." />
          </div>
        </div>
        <Button onClick={() => setElectOpen(true)} disabled={!unit}>
          <Plus /> Elect Committee
        </Button>
      </div>

      {!unit ? (
        <EmptyState icon={Users} title="Select a unit to view its Disciplinary Committee" />
      ) : isLoading ? (
        <Skeleton className="h-32" />
      ) : !committee ? (
        <EmptyState icon={Users} title="No Disciplinary Committee elected yet at this unit" />
      ) : (
        <Card>
          <CardContent className="pt-6">
            <p className="mb-3 text-sm text-muted-foreground">
              Elected {format(new Date(committee.elected_at), "MMM d, yyyy")}
            </p>
            <div className="flex flex-col gap-2">
              {committee.members.map((m) => (
                <div key={m.id} className="flex items-center justify-between text-sm">
                  <span>{m.full_name}</span>
                  <span className="text-xs text-muted-foreground">{m.membership_id}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      <ElectCommitteeDialog unit={unit} open={electOpen} onOpenChange={setElectOpen} />
    </div>
  );
}

function CasesTab() {
  const router = useRouter();
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["discipline-cases", "unit", unit?.id],
    queryFn: () => disciplineApi.listCases({ organizational_unit_id: unit!.id }),
    enabled: !!unit,
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <span className="text-xs text-muted-foreground">Unit</span>
        <div className="w-64">
          <UnitPicker value={unit} onChange={setUnit} placeholder="Select a unit..." />
        </div>
      </div>
      {!unit ? (
        <EmptyState icon={Gavel} title="Select a unit to view its cases" />
      ) : isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={Gavel} title="No cases at this unit" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((c) => (
            <Card
              key={c.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/discipline/cases/${c.id}`)}
            >
              <CardContent className="flex items-center gap-3 pt-6">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
                  <Gavel className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{c.respondent.full_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {c.grounds.replace(/_/g, " ")} ·{" "}
                    {format(new Date(c.reported_at), "MMM d, yyyy")}
                  </p>
                </div>
                {c.convene_overdue && (
                  <Badge variant="destructive">
                    <AlertTriangle className="size-3" /> Convene overdue
                  </Badge>
                )}
                <Badge variant={STATUS_VARIANT[c.status] ?? "outline"}>{c.status}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function SuspensionsTab() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(
    user?.organizational_unit
      ? { id: user.organizational_unit.id, name: user.organizational_unit.name }
      : null,
  );
  const [imposeOpen, setImposeOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["discipline-suspensions", unit?.id],
    queryFn: () => disciplineApi.listSuspensions(unit?.id),
  });

  const renewMutation = useMutation({
    mutationFn: (id: string) => disciplineApi.renewSuspension(id),
    onSuccess: () => {
      toast.success("Suspension renewed.");
      queryClient.invalidateQueries({ queryKey: ["discipline-suspensions"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not renew suspension."),
  });

  const endMutation = useMutation({
    mutationFn: (id: string) => disciplineApi.endSuspension(id),
    onSuccess: () => {
      toast.success("Suspension ended.");
      queryClient.invalidateQueries({ queryKey: ["discipline-suspensions"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not end suspension."),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          <span className="text-xs text-muted-foreground">Unit</span>
          <div className="w-64">
            <UnitPicker value={unit} onChange={setUnit} placeholder="Select a unit..." />
          </div>
        </div>
        <Button onClick={() => setImposeOpen(true)}>
          <Plus /> Impose Suspension
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={ShieldAlert} title="No suspensions" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((s) => (
            <Card key={s.id}>
              <CardContent className="flex items-center gap-3 pt-6">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-warning/10 text-warning">
                  <ShieldAlert className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{s.user.full_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {s.reason} · suspended {format(new Date(s.suspended_at), "MMM d, yyyy")}
                  </p>
                  {s.referral_overdue && (
                    <p className="mt-1 text-xs text-destructive">
                      Referral to Disciplinary Committee overdue - suspension has lapsed
                      (Article 46(2)/(3))
                    </p>
                  )}
                </div>
                <Badge variant={s.status === "ACTIVE" ? "warning" : "outline"}>{s.status}</Badge>
                {s.status === "ACTIVE" && (
                  <div className="flex shrink-0 gap-1.5">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => renewMutation.mutate(s.id)}
                      disabled={s.renewal_count >= 1 || renewMutation.isPending}
                    >
                      Renew
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => endMutation.mutate(s.id)}
                      disabled={endMutation.isPending}
                    >
                      End
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <ImposeSuspensionDialog open={imposeOpen} onOpenChange={setImposeOpen} />
    </div>
  );
}

export default function DisciplinePage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-display font-semibold">Discipline</h1>
        <p className="text-sm text-muted-foreground">
          Articles 46-47: Disciplinary Committees, cases, and precautionary suspensions
        </p>
      </div>

      <Tabs defaultValue="my-cases">
        <TabsList>
          <TabsTrigger value="my-cases">My Cases</TabsTrigger>
          <TabsTrigger value="cases">Cases</TabsTrigger>
          <TabsTrigger value="committee">Committee</TabsTrigger>
          <TabsTrigger value="suspensions">Suspensions</TabsTrigger>
        </TabsList>
        <TabsContent value="my-cases">
          <MyCasesTab />
        </TabsContent>
        <TabsContent value="cases">
          <CasesTab />
        </TabsContent>
        <TabsContent value="committee">
          <CommitteeTab />
        </TabsContent>
        <TabsContent value="suspensions">
          <SuspensionsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
