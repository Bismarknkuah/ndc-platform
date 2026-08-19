"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format, formatDistanceToNow } from "date-fns";
import { CheckCircle2, Mail, Megaphone, Plus, Radio, Users, Video } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateBroadcastDialog } from "@/components/messaging/create-broadcast-dialog";
import { CreateReportDialog } from "@/components/messaging/create-report-dialog";
import { CreateMeetingDialog } from "@/components/messaging/create-meeting-dialog";
import { MeetingDetailDialog } from "@/components/messaging/meeting-detail-dialog";
import { ReportDetailDialog } from "@/components/messaging/report-detail-dialog";
import * as messagingApi from "@/lib/api/messaging";
import type { Report } from "@/lib/api/messaging";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

function BroadcastsTab() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [createOpen, setCreateOpen] = useState(false);
  const canIssue = hasPermission(user, "messaging.broadcast.downward");

  const { data, isLoading } = useQuery({
    queryKey: ["broadcasts"],
    queryFn: () => messagingApi.listBroadcasts(),
  });

  const ackMutation = useMutation({
    mutationFn: (id: string) => messagingApi.acknowledgeBroadcast(id),
    onSuccess: () => {
      toast.success("Acknowledged.");
      queryClient.invalidateQueries({ queryKey: ["broadcasts"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not acknowledge."),
  });

  return (
    <div className="flex flex-col gap-4">
      {canIssue && (
        <div className="flex justify-end">
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> Issue Broadcast
          </Button>
        </div>
      )}

      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={Megaphone} title="No broadcasts yet" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((broadcast) => (
            <Card key={broadcast.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{broadcast.title}</p>
                      <Badge variant={broadcast.kind === "DIRECTIVE" ? "warning" : "outline"}>
                        {broadcast.kind}
                      </Badge>
                      {broadcast.priority !== "NORMAL" && (
                        <Badge variant={broadcast.priority === "URGENT" ? "destructive" : "outline"}>
                          {broadcast.priority}
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{broadcast.body}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {broadcast.issued_by.full_name} → {broadcast.target_unit.name} ·{" "}
                      {formatDistanceToNow(new Date(broadcast.created_at), { addSuffix: true })}
                    </p>
                  </div>
                  {broadcast.requires_acknowledgement && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => ackMutation.mutate(broadcast.id)}
                      disabled={ackMutation.isPending}
                    >
                      <CheckCircle2 className="size-3.5" /> Acknowledge
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateBroadcastDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}

function ReportsTab() {
  const user = useAuthStore((s) => s.user);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const canSubmit = hasPermission(user, "messaging.report.upward");

  const { data, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => messagingApi.listReports(),
  });

  return (
    <div className="flex flex-col gap-4">
      {canSubmit && (
        <div className="flex justify-end">
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> File Report
          </Button>
        </div>
      )}

      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={Radio} title="No reports yet" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((report) => (
            <Card
              key={report.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => setSelectedReport(report)}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium">{report.title}</p>
                    <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">
                      {report.body}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {report.submitting_unit.name} → {report.target_unit.name} ·{" "}
                      {formatDistanceToNow(new Date(report.created_at), { addSuffix: true })}
                    </p>
                  </div>
                  <Badge variant={report.status === "RESOLVED" ? "success" : "outline"}>
                    {report.status}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateReportDialog open={createOpen} onOpenChange={setCreateOpen} />
      <ReportDetailDialog
        report={selectedReport}
        open={!!selectedReport}
        onOpenChange={(open) => !open && setSelectedReport(null)}
      />
    </div>
  );
}

function MeetingsTab() {
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["meetings"],
    queryFn: () => messagingApi.listMeetings({ upcoming: true }),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setCreateOpen(true)}>
          <Plus /> Schedule Meeting
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={Video} title="No upcoming meetings" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((meeting) => (
            <Card
              key={meeting.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => setSelectedMeetingId(meeting.id)}
            >
              <CardContent className="flex items-center gap-3 pt-6">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-chart-3/10 text-chart-3">
                  <Video className="size-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{meeting.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {format(new Date(meeting.scheduled_start), "EEE, MMM d · h:mm a")} ·{" "}
                    {meeting.target_unit.name}
                  </p>
                </div>
                <Badge variant="outline">{meeting.meeting_type}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateMeetingDialog open={createOpen} onOpenChange={setCreateOpen} />
      <MeetingDetailDialog
        meetingId={selectedMeetingId}
        open={!!selectedMeetingId}
        onOpenChange={(open) => !open && setSelectedMeetingId(null)}
      />
    </div>
  );
}

export default function MessagingPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-display font-semibold">Messaging</h1>
        <p className="text-sm text-muted-foreground">
          Broadcasts, upward reports, and meetings. Chain-of-command communication
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Link href="/messaging/groups">
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-3 pt-6">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-chart-3/10 text-chart-3">
                <Users className="size-5" />
              </div>
              <div>
                <p className="font-medium">Discussion Groups</p>
                <p className="text-sm text-muted-foreground">Group chats you belong to</p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/messaging/direct">
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-3 pt-6">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-chart-4/10 text-chart-4">
                <Mail className="size-5" />
              </div>
              <div>
                <p className="font-medium">Direct Messages</p>
                <p className="text-sm text-muted-foreground">Private one-to-one conversations</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      <Tabs defaultValue="broadcasts">
        <TabsList>
          <TabsTrigger value="broadcasts">Broadcasts</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
          <TabsTrigger value="meetings">Meetings</TabsTrigger>
        </TabsList>
        <TabsContent value="broadcasts">
          <BroadcastsTab />
        </TabsContent>
        <TabsContent value="reports">
          <ReportsTab />
        </TabsContent>
        <TabsContent value="meetings">
          <MeetingsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
