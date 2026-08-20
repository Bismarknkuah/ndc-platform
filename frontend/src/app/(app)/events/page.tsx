"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { CalendarDays, CheckCircle2, Megaphone, Plus, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateEventCampaignDialog } from "@/components/events/create-campaign-dialog";
import { CreateEventDialog } from "@/components/events/create-event-dialog";
import * as eventsApi from "@/lib/api/events";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

function CampaignsTab() {
  const user = useAuthStore((s) => s.user);
  const canManage = hasPermission(user, "hierarchy.manage");
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["event-campaigns"],
    queryFn: () => eventsApi.listEventCampaigns(),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        {canManage && (
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> New Campaign
          </Button>
        )}
      </div>
      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={Megaphone} title="No campaigns yet" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.results.map((campaign) => (
            <Card key={campaign.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{campaign.title}</p>
                  <Badge variant="outline">{campaign.status}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">{campaign.target_unit.name}</p>
                {campaign.goal_description && (
                  <p className="mt-2 text-sm text-muted-foreground">{campaign.goal_description}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <CreateEventCampaignDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}

function EventsTab() {
  const user = useAuthStore((s) => s.user);
  const canManage = hasPermission(user, "hierarchy.manage");
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["events"],
    queryFn: () => eventsApi.listEvents({ upcoming: true }),
  });

  const rsvpMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "ATTENDING" | "DECLINED" }) =>
      eventsApi.rsvpToEvent(id, status),
    onSuccess: () => {
      toast.success("RSVP recorded.");
      queryClient.invalidateQueries({ queryKey: ["events"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not RSVP."),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        {canManage && (
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> New Event
          </Button>
        )}
      </div>
      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={CalendarDays} title="No upcoming events" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((event) => (
            <Card key={event.id}>
              <CardContent className="flex items-center gap-3 pt-6">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-chart-4/10 text-chart-4">
                  <CalendarDays className="size-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{event.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {format(new Date(event.scheduled_start), "EEE, MMM d · h:mm a")}
                    {event.location ? ` · ${event.location}` : ""} · {event.target_unit.name}
                  </p>
                </div>
                <Badge variant="outline">{event.event_type.replace("_", " ")}</Badge>
                <div className="flex shrink-0 gap-1.5">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => rsvpMutation.mutate({ id: event.id, status: "ATTENDING" })}
                    disabled={rsvpMutation.isPending}
                  >
                    <CheckCircle2 className="size-3.5 text-success" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => rsvpMutation.mutate({ id: event.id, status: "DECLINED" })}
                    disabled={rsvpMutation.isPending}
                  >
                    <XCircle className="size-3.5 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <CreateEventDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}

export default function EventsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-display font-semibold">Events & Campaigns</h1>
        <p className="text-sm text-muted-foreground">
          Rallies, town halls, fundraisers, and the campaigns that group them
        </p>
      </div>
      <Tabs defaultValue="events">
        <TabsList>
          <TabsTrigger value="events">Events</TabsTrigger>
          <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
        </TabsList>
        <TabsContent value="events">
          <EventsTab />
        </TabsContent>
        <TabsContent value="campaigns">
          <CampaignsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
