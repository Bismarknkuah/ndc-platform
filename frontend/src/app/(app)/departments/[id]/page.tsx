"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Plus, UserPlus, Users } from "lucide-react";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { EmptyState } from "@/components/shared/empty-state";
import { UnitPicker } from "@/components/shared/unit-picker";
import { AddTeamMemberDialog } from "@/components/departments/add-team-member-dialog";
import { AssignTaskDialog } from "@/components/departments/assign-task-dialog";
import * as departmentsApi from "@/lib/api/departments";
import { useAuthStore } from "@/stores/auth-store";

export default function DepartmentTeamPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  const [unit, setUnit] = useState<{ id: string; name: string } | null>(
    user?.organizational_unit
      ? { id: user.organizational_unit.id, name: user.organizational_unit.name }
      : null,
  );
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [assignTaskOpen, setAssignTaskOpen] = useState(false);

  const {
    data: dashboard,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["team-dashboard", params.id, unit?.id],
    queryFn: () => departmentsApi.getTeamDashboard(params.id, unit!.id),
    enabled: !!unit,
  });

  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" size="sm" className="w-fit" onClick={() => router.push("/departments")}>
        ← Back to Departments
      </Button>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <Label>Viewing team at</Label>
          <div className="w-72">
            <UnitPicker value={unit} onChange={setUnit} placeholder="Select a unit..." />
          </div>
        </div>
        {dashboard && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setAddMemberOpen(true)}>
              <UserPlus /> Add Member
            </Button>
            <Button onClick={() => setAssignTaskOpen(true)}>
              <Plus /> Assign Task
            </Button>
          </div>
        )}
      </div>

      {!unit ? (
        <EmptyState icon={Users} title="Select a unit to view its team" compact />
      ) : isLoading ? (
        <Skeleton className="h-64" />
      ) : isError || !dashboard ? (
        <EmptyState
          icon={Users}
          title="No access or no team here"
          description="You may not have authority over this department at this unit, or no team exists here yet."
          compact
        />
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-display font-semibold">{dashboard.team_size}</p>
                <p className="text-xs text-muted-foreground">Team members</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-display font-semibold">
                  {dashboard.total_pending_tasks}
                </p>
                <p className="text-xs text-muted-foreground">Pending tasks</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-display font-semibold">
                  {dashboard.upcoming_tasks.length}
                </p>
                <p className="text-xs text-muted-foreground">Upcoming this diary</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Roster</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {dashboard.roster.length === 0 ? (
                  <EmptyState icon={Users} title="No team members yet" compact />
                ) : (
                  <ul className="divide-y divide-border">
                    {dashboard.roster.map((member) => (
                      <li key={member.user.id} className="flex items-center justify-between px-4 py-3">
                        <div>
                          <p className="text-sm font-medium">{member.user.full_name}</p>
                          <p className="text-xs text-muted-foreground">{member.position}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          {member.pending_tasks > 0 && (
                            <Badge variant="warning">{member.pending_tasks} pending</Badge>
                          )}
                          <Badge variant="outline">{member.completed_tasks_this_week} done this wk</Badge>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Upcoming Diary</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {dashboard.upcoming_tasks.length === 0 ? (
                  <EmptyState icon={CalendarClock} title="Nothing scheduled" compact />
                ) : (
                  <ul className="divide-y divide-border">
                    {dashboard.upcoming_tasks.map((task) => (
                      <li key={task.id} className="px-4 py-3">
                        <p className="text-sm font-medium">{task.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {task.assigned_to.full_name} · {task.engagement_type}
                          {task.platform_name ? ` · ${task.platform_name}` : ""} ·{" "}
                          {format(new Date(task.scheduled_at), "MMM d, h:mm a")}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          <AddTeamMemberDialog
            departmentId={params.id}
            organizationalUnitId={unit.id}
            open={addMemberOpen}
            onOpenChange={setAddMemberOpen}
          />
          <AssignTaskDialog
            departmentId={params.id}
            roster={dashboard.roster}
            open={assignTaskOpen}
            onOpenChange={setAssignTaskOpen}
          />
        </>
      )}
    </div>
  );
}
