"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { CheckCircle2, Loader2, Video, XCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import * as messagingApi from "@/lib/api/messaging";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";

export function MeetingDetailDialog({
  meetingId,
  open,
  onOpenChange,
}: {
  meetingId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const { data: meeting, isLoading } = useQuery({
    queryKey: ["meeting", meetingId],
    queryFn: () => messagingApi.getMeeting(meetingId!),
    enabled: !!meetingId && open,
  });

  const { data: minutes } = useQuery({
    queryKey: ["meeting-minutes", meetingId],
    queryFn: () => messagingApi.getMeetingMinutes(meetingId!),
    enabled: !!meetingId && open && meeting?.status === "COMPLETED",
    retry: false,
  });

  const rsvpMutation = useMutation({
    mutationFn: (status: "ATTENDING" | "DECLINED") =>
      messagingApi.rsvpToMeeting(meetingId!, status),
    onSuccess: (_, status) => {
      toast.success(status === "ATTENDING" ? "You're marked as attending." : "RSVP recorded.");
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not RSVP."),
  });

  const isHost = meeting?.host.id === user?.id;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {isLoading || !meeting ? (
          <div className="flex justify-center py-8">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>{meeting.title}</DialogTitle>
              <DialogDescription>
                {meeting.meeting_type === "WORKSHOP" ? "Training Workshop" : "Meeting"} ·{" "}
                {meeting.target_unit.name}
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-col gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Host</span>
                <span>{meeting.host.full_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Starts</span>
                <span>{format(new Date(meeting.scheduled_start), "EEE, MMM d, h:mm a")}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Ends</span>
                <span>{format(new Date(meeting.scheduled_end), "EEE, MMM d, h:mm a")}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <Badge variant="outline">{meeting.status}</Badge>
              </div>
              {meeting.description && <p className="text-muted-foreground">{meeting.description}</p>}
            </div>

            {meeting.status === "SCHEDULED" && (
              <>
                <Separator />
                <a href={meeting.meeting_url} target="_blank" rel="noreferrer">
                  <Button className="w-full">
                    <Video /> Join Video Room
                  </Button>
                </a>
                {!isHost && (
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => rsvpMutation.mutate("ATTENDING")}
                      disabled={rsvpMutation.isPending}
                    >
                      <CheckCircle2 className="text-success" /> Attending
                    </Button>
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => rsvpMutation.mutate("DECLINED")}
                      disabled={rsvpMutation.isPending}
                    >
                      <XCircle className="text-destructive" /> Can&apos;t attend
                    </Button>
                  </div>
                )}
              </>
            )}

            {minutes && (
              <>
                <Separator />
                <div>
                  <p className="text-sm font-medium">Minutes</p>
                  {minutes.summary && (
                    <p className="mt-1 text-sm text-muted-foreground">{minutes.summary}</p>
                  )}
                  {minutes.action_items.length > 0 && (
                    <ul className="mt-2 flex flex-col gap-1">
                      {minutes.action_items.map((item, i) => (
                        <li key={i} className="text-xs text-muted-foreground">
                          • {item.description}
                          {item.assigned_to && ` (${item.assigned_to.full_name})`}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
