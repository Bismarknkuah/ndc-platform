"use client";

import { LineChart, Line, XAxis, Tooltip, ResponsiveContainer } from "recharts";
import { AlertTriangle, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AnimatedNumber } from "@/components/shared/animated-number";
import type { JurisdictionSummary } from "@/lib/api/dashboard";

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-2xl font-display font-semibold leading-none">
        <AnimatedNumber value={value} />
      </p>
      <p className="text-xs text-muted-foreground mt-1">{label}</p>
    </div>
  );
}

export function JurisdictionSummaryCard({ summary }: { summary: JurisdictionSummary }) {
  const chartData = summary.growth_last_12_months.map((m) => ({
    month: m.month.slice(5),
    members: m.new_members,
  }));

  return (
    <Card className="border-primary/20">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-base">
          <Users className="size-4 text-primary" />
          Your Jurisdiction: {summary.organizational_unit.name}
        </CardTitle>
        {summary.requires_attention > 0 && (
          <Badge variant="warning">
            <AlertTriangle className="size-3" />
            {summary.requires_attention} need{summary.requires_attention === 1 ? "s" : ""}{" "}
            attention
          </Badge>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <MiniStat label="Total Members" value={summary.total_members} />
          <MiniStat label="Executives" value={summary.executive_count} />
          <MiniStat label="Pending Complaints" value={summary.pending_complaints} />
          <MiniStat label="Pending Welfare" value={summary.pending_welfare_requests} />
        </div>

        {chartData.some((d) => d.members > 0) && (
          <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="members"
                  stroke="var(--color-primary)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
