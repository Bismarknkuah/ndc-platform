"use client";

import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis, ResponsiveContainer } from "recharts";
import type { FinanceCategoryTotal } from "@/lib/api/dashboard";
import { EmptyState } from "@/components/shared/empty-state";
import { PieChart as PieChartIcon } from "lucide-react";

export function FinanceBreakdownChart({ categories }: { categories: FinanceCategoryTotal[] }) {
  if (categories.length === 0) {
    return (
      <EmptyState
        icon={PieChartIcon}
        title="No approved finance records yet"
        description="Income and expense breakdowns will appear here once records are approved."
        compact
      />
    );
  }

  const data = categories.map((c) => ({
    name: c.category,
    amount: Number(c.total),
    type: c.record_type,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
          <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
          <YAxis
            type="category"
            dataKey="name"
            width={130}
            tick={{ fontSize: 11 }}
            stroke="var(--muted-foreground)"
          />
          <Tooltip
            formatter={(value) => [`GHS ${Number(value).toLocaleString()}`, "Amount"]}
            contentStyle={{
              backgroundColor: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Bar dataKey="amount" radius={[0, 4, 4, 0]} fill="var(--color-chart-1)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
