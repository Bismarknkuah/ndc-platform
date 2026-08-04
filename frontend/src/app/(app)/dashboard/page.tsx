"use client";

import { Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { format, formatDistanceToNow } from "date-fns";
import {
  Bell,
  CalendarClock,
  CheckSquare,
  ClipboardList,
  Coins,
  Megaphone,
  Users,
  Vote,
  Video,
} from "lucide-react";
import { fetchDashboard } from "@/lib/api/dashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FinanceBreakdownChart } from "@/components/dashboard/finance-breakdown-chart";
import { JurisdictionSummaryCard } from "@/components/dashboard/jurisdiction-summary-card";
import { ExecutiveAiPanel } from "@/components/dashboard/executive-ai-panel";
import { DuesPaymentCard } from "@/components/dashboard/dues-payment-card";
import { DepartmentQuickActions } from "@/components/dashboard/department-quick-actions";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { AnimatedNumber } from "@/components/shared/animated-number";
import { StaggerContainer, StaggerItem } from "@/components/shared/stagger-list";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: number | string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 pt-6">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="size-5" />
        </div>
        <div>
          <p className="text-2xl font-display font-semibold leading-none">
            {typeof value === "number" ? <AnimatedNumber value={value} /> : value}
          </p>
          <p className="text-xs text-muted-foreground mt-1">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}

export default function DashboardPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  if (isLoading) return <DashboardSkeleton />;
  if (isError || !data) {
    return (
      <ErrorState
        title="Couldn't load your dashboard"
        description="Something went wrong reaching the server."
        onRetry={() => refetch()}
      />
    );
  }

  const { profile } = data;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-display font-semibold">
          Welcome, {profile.first_name}
        </h1>
        <p className="text-sm text-muted-foreground">
          {profile.role?.name ?? "Ordinary Member"}
          {profile.organizational_unit ? ` · ${profile.organizational_unit.name}` : ""}
        </p>
      </div>

      {data.jurisdiction_summary ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <JurisdictionSummaryCard summary={data.jurisdiction_summary} />
          <ExecutiveAiPanel jurisdictionSummary={data.jurisdiction_summary} />
        </div>
      ) : (
        <Suspense fallback={<Skeleton className="h-48" />}>
          <DuesPaymentCard />
        </Suspense>
      )}

      <StaggerContainer className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StaggerItem>
          <StatCard icon={Bell} label="Unread notifications" value={data.unread_notification_count} />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={ClipboardList} label="Pending tasks" value={data.pending_tasks.length} />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={CalendarClock} label="Upcoming meetings" value={data.upcoming_meetings.length} />
        </StaggerItem>
        <StaggerItem>
          {data.teams_led ? (
            <StatCard icon={Users} label="Teams led" value={data.teams_led.length} />
          ) : (
            <StatCard icon={Megaphone} label="Recent broadcasts" value={data.recent_broadcasts.length} />
          )}
        </StaggerItem>
      </StaggerContainer>

      {data.teams_led && data.teams_led.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-lg font-semibold">Your Department</h2>
          <DepartmentQuickActions teamsLed={data.teams_led} />
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">Upcoming Meetings</h2>
            <Link href="/messaging" className="text-xs text-muted-foreground hover:text-foreground">
              View all
            </Link>
          </div>
          <Card>
            <CardContent className="p-0">
              {data.upcoming_meetings.length === 0 ? (
                <EmptyState
                  icon={Video}
                  title="No upcoming meetings"
                  description="Meetings you host or are invited to will show up here."
                  compact
                />
              ) : (
                <ul className="divide-y divide-border">
                  {data.upcoming_meetings.map((meeting) => (
                    <li key={meeting.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-chart-3/10 text-chart-3">
                        <Video className="size-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{meeting.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(meeting.scheduled_start), "EEE, MMM d · h:mm a")}
                        </p>
                      </div>
                      <Badge variant="outline">{meeting.meeting_type}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">Pending Tasks</h2>
            <Link href="/departments" className="text-xs text-muted-foreground hover:text-foreground">
              View all
            </Link>
          </div>
          <Card>
            <CardContent className="p-0">
              {data.pending_tasks.length === 0 ? (
                <EmptyState
                  icon={CheckSquare}
                  title="Nothing pending"
                  description="Department tasks assigned to you will show up here."
                  compact
                />
              ) : (
                <ul className="divide-y divide-border">
                  {data.pending_tasks.map((task) => (
                    <li key={task.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-chart-2/10 text-chart-2">
                        <ClipboardList className="size-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{task.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {task.engagement_type} · {task.platform_name} ·{" "}
                          {formatDistanceToNow(new Date(task.scheduled_at), { addSuffix: true })}
                        </p>
                      </div>
                      <Badge variant={task.status === "ACKNOWLEDGED" ? "secondary" : "warning"}>
                        {task.status}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </section>
      </div>

      {data.active_elections && data.active_elections.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-lg font-semibold">Active Elections</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.active_elections.map((election) => (
              <Link key={election.id} href={`/elections/${election.id}`}>
                <Card className="transition-shadow hover:shadow-md">
                  <CardContent className="flex items-start gap-3 pt-6">
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-accent/15 text-accent">
                      <Vote className="size-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-medium">{election.title}</p>
                      <p className="text-xs text-muted-foreground">{election.scope_unit.name}</p>
                      <Badge className="mt-1.5" variant="success">
                        {election.status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {data.upcoming_events && data.upcoming_events.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-lg font-semibold">Upcoming Events</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.upcoming_events.map((event) => (
              <Card key={event.id}>
                <CardContent className="pt-6">
                  <p className="font-medium">{event.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {format(new Date(event.scheduled_start), "EEE, MMM d · h:mm a")}
                  </p>
                  {event.location && (
                    <p className="text-xs text-muted-foreground">{event.location}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {data.recent_broadcasts.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-lg font-semibold">Recent Broadcasts</h2>
          <Card>
            <CardContent className="p-0">
              <ul className="divide-y divide-border">
                {data.recent_broadcasts.map((broadcast) => (
                  <li key={broadcast.id} className="flex items-start gap-3 px-4 py-3">
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <Megaphone className="size-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{broadcast.title}</p>
                      <p className="line-clamp-1 text-xs text-muted-foreground">{broadcast.body}</p>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(broadcast.created_at), { addSuffix: true })}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </section>
      )}

      {data.finance_summary && (
        <section>
          <h2 className="mb-3 font-display text-lg font-semibold">Finance Summary</h2>
          <Card>
            <CardHeader className="flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {data.finance_summary.organizational_unit.name}
              </CardTitle>
              <div className="flex items-center gap-1 text-sm">
                <Coins className="size-4 text-primary" />
                <span className="font-display font-semibold">
                  GHS {data.finance_summary.net_balance}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <FinanceBreakdownChart categories={data.finance_summary.by_category} />
            </CardContent>
          </Card>
        </section>
      )}

      {data.jurisdiction_summary && (
        <section>
          <h2 className="mb-3 font-display text-lg font-semibold">Your Own Dues</h2>
          <Suspense fallback={<Skeleton className="h-48" />}>
            <DuesPaymentCard />
          </Suspense>
        </section>
      )}
    </div>
  );
}
