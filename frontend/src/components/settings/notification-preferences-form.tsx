"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import * as messagingApi from "@/lib/api/messaging";
import { ApiError } from "@/lib/api/client";

const CHANNELS: {
  key: "email_enabled" | "sms_enabled" | "push_enabled";
  label: string;
  description: string;
}[] = [
  {
    key: "email_enabled",
    label: "Email",
    description: "Broadcasts, meeting invites, and reports via email",
  },
  {
    key: "sms_enabled",
    label: "SMS",
    description: "Urgent broadcasts and election-day alerts via text message",
  },
  {
    key: "push_enabled",
    label: "Push notifications",
    description: "Real-time alerts on the mobile app",
  },
];

export function NotificationPreferencesForm() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: messagingApi.getNotificationPreferences,
  });

  const mutation = useMutation({
    mutationFn: (payload: Partial<messagingApi.NotificationPreference>) =>
      messagingApi.updateNotificationPreferences(payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["notification-preferences"], updated);
      toast.success("Preferences saved.");
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not save preferences."),
  });

  if (isLoading || !data) return <Skeleton className="h-40" />;

  return (
    <div className="flex flex-col gap-4">
      {CHANNELS.map((channel) => (
        <div
          key={channel.key}
          className="flex items-center justify-between rounded-lg border border-border p-3"
        >
          <div>
            <Label>{channel.label}</Label>
            <p className="text-xs text-muted-foreground">{channel.description}</p>
          </div>
          <Switch
            checked={data[channel.key]}
            onCheckedChange={(checked) => mutation.mutate({ [channel.key]: checked })}
            disabled={mutation.isPending}
          />
        </div>
      ))}
    </div>
  );
}
