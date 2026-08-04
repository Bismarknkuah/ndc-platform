"use client";

import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis, ResponsiveContainer } from "recharts";

const COLORS: Record<string, string> = {
  Male: "var(--color-chart-1)",
  Female: "var(--color-chart-2)",
  Other: "var(--color-chart-3)",
  Unspecified: "var(--color-chart-4)",
};

export function GenderBreakdownChart({
  breakdown,
}: {
  breakdown: { MALE: number; FEMALE: number; OTHER: number; UNSPECIFIED: number };
}) {
  const data = [
    { name: "Male", count: breakdown.MALE },
    { name: "Female", count: breakdown.FEMALE },
    { name: "Other", count: breakdown.OTHER },
    { name: "Unspecified", count: breakdown.UNSPECIFIED },
  ].filter((d) => d.count > 0);

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: -20, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
          <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" allowDecimals={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={COLORS[entry.name]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
