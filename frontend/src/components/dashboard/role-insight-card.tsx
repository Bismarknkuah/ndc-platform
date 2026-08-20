import { CalendarClock, ShieldCheck, Users } from "lucide-react";
import { format } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RoleInsight } from "@/lib/api/dashboard";

const WIDGET_ICONS = {
  secretary: CalendarClock,
  wing: Users,
  auditor: ShieldCheck,
} as const;

export function RoleInsightCard({ insight }: { insight: RoleInsight }) {
  const Icon = WIDGET_ICONS[insight.widget];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="size-4 text-primary" />
          {insight.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {insight.stats.map((stat) => (
            <div key={stat.label}>
              <p className="font-display text-lg font-semibold leading-none">{stat.value}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{stat.label}</p>
            </div>
          ))}
        </div>

        {insight.upcoming_meetings && insight.upcoming_meetings.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground">Next up</p>
            <div className="flex flex-col gap-1.5">
              {insight.upcoming_meetings.map((m) => (
                <div key={m.id} className="flex items-center justify-between text-sm">
                  <span>{m.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {format(new Date(m.scheduled_start), "MMM d, h:mm a")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {insight.recent_actions && insight.recent_actions.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground">Recent activity</p>
            <div className="flex flex-col gap-1.5">
              {insight.recent_actions.map((a, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-xs">{a.action}</span>
                  <span className="text-xs text-muted-foreground">{a.actor_email}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {insight.note && <p className="text-xs text-muted-foreground">{insight.note}</p>}
      </CardContent>
    </Card>
  );
}
