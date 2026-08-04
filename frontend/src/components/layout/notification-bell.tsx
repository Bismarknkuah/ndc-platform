"use client";

import Link from "next/link";
import { Bell, CheckCheck } from "lucide-react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import * as messagingApi from "@/lib/api/messaging";
import { cn } from "@/lib/utils";

const NOTIFICATION_TYPE_ICON_COLOR: Record<string, string> = {
  BROADCAST: "bg-primary",
  ELECTION_ELIGIBILITY: "bg-accent",
  MEETING: "bg-chart-3",
  EVENT: "bg-chart-4",
  TASK: "bg-chart-2",
};

export function NotificationBell() {
  const queryClient = useQueryClient();

  const { data: unreadCount = 0 } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: messagingApi.fetchUnreadCount,
    refetchInterval: 30_000,
  });

  const { data: notificationsPage } = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () => messagingApi.fetchNotifications({ page: 1 }),
    refetchInterval: 30_000,
  });

  const markAllRead = useMutation({
    mutationFn: messagingApi.markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const notifications = notificationsPage?.results.slice(0, 8) ?? [];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between px-3 py-2">
          <p className="text-sm font-medium">Notifications</p>
          {unreadCount > 0 && (
            <button
              onClick={() => markAllRead.mutate()}
              className="flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              <CheckCheck className="size-3.5" />
              Mark all read
            </button>
          )}
        </div>
        <DropdownMenuSeparator />
        <ScrollArea className="max-h-80">
          {notifications.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">
              You&apos;re all caught up.
            </p>
          ) : (
            notifications.map((notification) => (
              <div
                key={notification.id}
                className={cn(
                  "flex gap-2.5 px-3 py-2.5 text-sm border-b border-border last:border-b-0",
                  !notification.is_read && "bg-secondary/50",
                )}
              >
                <span
                  className={cn(
                    "mt-1.5 size-1.5 shrink-0 rounded-full",
                    NOTIFICATION_TYPE_ICON_COLOR[notification.notification_type] ?? "bg-muted-foreground",
                  )}
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{notification.title}</p>
                  <p className="line-clamp-2 text-xs text-muted-foreground">{notification.body}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground/70">
                    {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                  </p>
                </div>
              </div>
            ))
          )}
        </ScrollArea>
        <DropdownMenuSeparator />
        <Link
          href="/notifications"
          className="block px-3 py-2 text-center text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          View all notifications
        </Link>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
