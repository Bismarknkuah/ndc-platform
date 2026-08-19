"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { Coins, Plus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { UnitPicker } from "@/components/shared/unit-picker";
import { EmptyState } from "@/components/shared/empty-state";
import { FinanceBreakdownChart } from "@/components/dashboard/finance-breakdown-chart";
import { RecordFinanceDialog } from "@/components/finance/record-finance-dialog";
import * as financeApi from "@/lib/api/finance";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";

export default function FinancePage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(
    user?.organizational_unit
      ? { id: user.organizational_unit.id, name: user.organizational_unit.name }
      : null,
  );
  const [recordOpen, setRecordOpen] = useState(false);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["finance-summary", unit?.id],
    queryFn: () => financeApi.getFinanceSummary(unit!.id),
    enabled: !!unit,
  });

  const { data: records, isLoading: recordsLoading } = useQuery({
    queryKey: ["finance-records", unit?.id],
    queryFn: () => financeApi.listFinanceRecords({ organizational_unit_id: unit!.id }),
    enabled: !!unit,
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "APPROVED" | "REJECTED" }) =>
      financeApi.updateFinanceRecordStatus(id, status),
    onSuccess: () => {
      toast.success("Record updated.");
      queryClient.invalidateQueries({ queryKey: ["finance-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not update record."),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-semibold">Finance</h1>
          <p className="text-sm text-muted-foreground">
            Income, expenses, and approvals, rolled up across a unit&apos;s whole subtree
          </p>
        </div>
        <div className="flex items-end gap-3">
          <div className="flex flex-col gap-1.5">
            <span className="text-xs text-muted-foreground">Viewing</span>
            <div className="w-64">
              <UnitPicker value={unit} onChange={setUnit} placeholder="Select a unit..." />
            </div>
          </div>
          <Button onClick={() => setRecordOpen(true)} disabled={!unit}>
            <Plus /> Record Entry
          </Button>
        </div>
      </div>

      {!unit ? (
        <EmptyState icon={Coins} title="Select a unit to view its finances" />
      ) : (
        <>
          {summaryLoading ? (
            <Skeleton className="h-64" />
          ) : summary ? (
            <Card>
              <CardHeader className="flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {summary.organizational_unit.name}
                </CardTitle>
                <div className="flex items-center gap-1 text-sm">
                  <Coins className="size-4 text-primary" />
                  <span className="font-display font-semibold">
                    GHS {Number(summary.net_balance).toLocaleString()}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4 grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-lg font-display font-semibold text-success">
                      GHS {Number(summary.total_income).toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">Total income</p>
                  </div>
                  <div>
                    <p className="text-lg font-display font-semibold text-destructive">
                      GHS {Number(summary.total_expense).toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">Total expense</p>
                  </div>
                  <div>
                    <p className="text-lg font-display font-semibold">{summary.record_count}</p>
                    <p className="text-xs text-muted-foreground">Approved records</p>
                  </div>
                </div>
                <FinanceBreakdownChart categories={summary.by_category} />
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Records</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {recordsLoading ? (
                <div className="p-4">
                  <Skeleton className="h-32" />
                </div>
              ) : !records || records.results.length === 0 ? (
                <EmptyState icon={Coins} title="No finance records yet" compact />
              ) : (
                <ul className="divide-y divide-border">
                  {records.results.map((record) => (
                    <li key={record.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium">{record.category}</p>
                          <Badge variant={record.record_type === "INCOME" ? "success" : "destructive"}>
                            {record.record_type}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {record.recorded_by.full_name} ·{" "}
                          {format(new Date(record.record_date), "MMM d, yyyy")}
                          {record.description ? ` · ${record.description}` : ""}
                        </p>
                      </div>
                      <p className="shrink-0 font-mono text-sm font-medium">
                        GHS {Number(record.amount).toLocaleString()}
                      </p>
                      {record.status === "PENDING" ? (
                        <div className="flex shrink-0 gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              statusMutation.mutate({ id: record.id, status: "APPROVED" })
                            }
                            disabled={statusMutation.isPending}
                          >
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:text-destructive"
                            onClick={() =>
                              statusMutation.mutate({ id: record.id, status: "REJECTED" })
                            }
                            disabled={statusMutation.isPending}
                          >
                            Reject
                          </Button>
                        </div>
                      ) : (
                        <Badge
                          variant={record.status === "APPROVED" ? "success" : "outline"}
                          className="shrink-0"
                        >
                          {record.status}
                        </Badge>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <RecordFinanceDialog
            organizationalUnitId={unit.id}
            open={recordOpen}
            onOpenChange={setRecordOpen}
          />
        </>
      )}
    </div>
  );
}
