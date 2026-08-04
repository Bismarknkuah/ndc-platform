"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Map as MapIcon, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UnitPicker } from "@/components/shared/unit-picker";
import { EmptyState } from "@/components/shared/empty-state";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { GrowthChart } from "@/components/analytics/growth-chart";
import { GenderBreakdownChart } from "@/components/analytics/gender-breakdown-chart";
import { GISMap } from "@/components/analytics/gis-map";
import * as analyticsApi from "@/lib/api/analytics";
import * as departmentsApi from "@/lib/api/departments";
import { ALL_UNIT_TYPES, unitTypeLabel } from "@/lib/api/hierarchy";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

function MembershipTab({ unit }: { unit: { id: string; name: string } | null }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["membership-analytics", unit?.id],
    queryFn: () => analyticsApi.getMembershipAnalytics(unit!.id),
    enabled: !!unit,
  });

  if (!unit) return <EmptyState icon={Users} title="Select a unit to view analytics" compact />;
  if (isLoading) return <Skeleton className="h-64" />;
  if (isError || !data) {
    return (
      <ForbiddenState description="You don't have analytics authority over this jurisdiction." />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-display font-semibold">{data.total_members}</p>
            <p className="text-xs text-muted-foreground">Total members</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-display font-semibold">{data.executive_count}</p>
            <p className="text-xs text-muted-foreground">Executives</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-display font-semibold">{data.ordinary_member_count}</p>
            <p className="text-xs text-muted-foreground">Ordinary members</p>
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Growth (last 12 months)</CardTitle>
          </CardHeader>
          <CardContent>
            <GrowthChart data={data.growth_last_12_months} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Gender Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <GenderBreakdownChart breakdown={data.gender_breakdown} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DepartmentsTab({ unit }: { unit: { id: string; name: string } | null }) {
  const [departmentId, setDepartmentId] = useState<string>("");

  const { data: departments } = useQuery({
    queryKey: ["departments"],
    queryFn: departmentsApi.listDepartments,
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: ["department-analytics", departmentId, unit?.id],
    queryFn: () => analyticsApi.getDepartmentAnalytics(departmentId, unit!.id),
    enabled: !!unit && !!departmentId,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <Label>Department</Label>
        <Select value={departmentId} onValueChange={setDepartmentId}>
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Select a department..." />
          </SelectTrigger>
          <SelectContent>
            {departments?.map((d) => (
              <SelectItem key={d.id} value={d.id}>
                {d.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {!unit || !departmentId ? (
        <EmptyState icon={BarChart3} title="Select a unit and department" compact />
      ) : isLoading ? (
        <Skeleton className="h-48" />
      ) : isError || !data ? (
        <ForbiddenState description="You don't have authority over this department at this unit." />
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-display font-semibold">{data.team_size}</p>
                <p className="text-xs text-muted-foreground">Team size</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-display font-semibold">{data.total_tasks}</p>
                <p className="text-xs text-muted-foreground">Total tasks</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-display font-semibold">
                  {data.completion_rate_percentage != null
                    ? `${data.completion_rate_percentage}%`
                    : "—"}
                </p>
                <p className="text-xs text-muted-foreground">Completion rate</p>
              </CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Task Status Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-4 gap-4">
              {Object.entries(data.status_breakdown).map(([status, count]) => (
                <div key={status}>
                  <p className="text-lg font-display font-semibold">{count}</p>
                  <p className="text-xs text-muted-foreground">{status}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function MapTab({ unit }: { unit: { id: string; name: string } | null }) {
  const [unitTypeFilter, setUnitTypeFilter] = useState<string>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["gis-map", unit?.id, unitTypeFilter],
    queryFn: () => analyticsApi.getGISMap(unit!.id, unitTypeFilter === "all" ? undefined : unitTypeFilter),
    enabled: !!unit,
  });

  if (!unit) return <EmptyState icon={MapIcon} title="Select a unit to view the map" compact />;

  return (
    <div className="flex flex-col gap-4">
      <Select value={unitTypeFilter} onValueChange={setUnitTypeFilter}>
        <SelectTrigger size="sm" className="w-52">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All unit types</SelectItem>
          {ALL_UNIT_TYPES.map((type) => (
            <SelectItem key={type} value={type}>
              {unitTypeLabel(type)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isLoading ? (
        <Skeleton className="h-[500px]" />
      ) : !data || data.features.length === 0 ? (
        <EmptyState
          icon={MapIcon}
          title="No units with coordinates yet"
          description="Only units that have had latitude/longitude set appear here."
        />
      ) : (
        <GISMap features={data.features} />
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  const user = useAuthStore((s) => s.user);
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(
    user?.organizational_unit
      ? { id: user.organizational_unit.id, name: user.organizational_unit.name }
      : null,
  );

  const canView = hasPermission(user, "hierarchy.manage") || (user?.is_superadmin ?? false);

  if (!canView) {
    return (
      <ForbiddenState description="Analytics requires hierarchy authority, or department-level authority for the Departments tab." />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-semibold">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Membership growth, department performance, and geographic distribution
          </p>
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="text-xs text-muted-foreground">Jurisdiction</span>
          <div className="w-64">
            <UnitPicker value={unit} onChange={setUnit} placeholder="Select a unit..." />
          </div>
        </div>
      </div>

      <Tabs defaultValue="membership">
        <TabsList>
          <TabsTrigger value="membership">Membership</TabsTrigger>
          <TabsTrigger value="departments">Departments</TabsTrigger>
          <TabsTrigger value="map">Map</TabsTrigger>
        </TabsList>
        <TabsContent value="membership">
          <MembershipTab unit={unit} />
        </TabsContent>
        <TabsContent value="departments">
          <DepartmentsTab unit={unit} />
        </TabsContent>
        <TabsContent value="map">
          <MapTab unit={unit} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
