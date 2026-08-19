"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Mail, MessageCircle, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { UserPicker } from "@/components/shared/user-picker";
import { EmptyState } from "@/components/shared/empty-state";
import * as dmApi from "@/lib/api/direct-messages";
import { useAuthStore } from "@/stores/auth-store";

interface ConversationSummary {
  otherUserId: string;
  otherUserName: string;
  lastMessage: string;
  lastMessageAt: string;
  unread: boolean;
}

export default function DirectMessagesInboxPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const [newConversationOpen, setNewConversationOpen] = useState(false);
  const [recipient, setRecipient] = useState<{ id: string; full_name: string } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["direct-messages", "inbox"],
    queryFn: () => dmApi.listDirectMessages(),
    refetchInterval: 15000,
  });

  // The API returns every DM sent to/from the caller, newest-first, with
  // no conversation concept server-side - group by the "other party"
  // client-side to build an inbox view.
  const conversations = useMemo<ConversationSummary[]>(() => {
    if (!data || !user) return [];
    const byUser = new Map<string, ConversationSummary>();
    for (const message of data.results) {
      const isOutgoing = message.sender.id === user.id;
      const other = isOutgoing ? message.recipient : message.sender;
      if (!byUser.has(other.id)) {
        byUser.set(other.id, {
          otherUserId: other.id,
          otherUserName: other.full_name,
          lastMessage: message.body,
          lastMessageAt: message.created_at,
          unread: !isOutgoing && message.read_at === null,
        });
      }
    }
    return Array.from(byUser.values());
  }, [data, user]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Direct Messages</h1>
          <p className="text-sm text-muted-foreground">Private one-to-one conversations</p>
        </div>
        <Button onClick={() => setNewConversationOpen(true)}>
          <Plus /> New Message
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : conversations.length === 0 ? (
        <EmptyState icon={Mail} title="No conversations yet" />
      ) : (
        <div className="flex flex-col gap-2">
          {conversations.map((conversation) => (
            <Card
              key={conversation.otherUserId}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/messaging/direct/${conversation.otherUserId}`)}
            >
              <CardContent className="flex items-center gap-3 pt-6">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary text-muted-foreground">
                  <MessageCircle className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{conversation.otherUserName}</p>
                  <p className="line-clamp-1 text-sm text-muted-foreground">
                    {conversation.lastMessage}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(conversation.lastMessageAt), {
                      addSuffix: true,
                    })}
                  </span>
                  {conversation.unread && <Badge variant="success">New</Badge>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={newConversationOpen} onOpenChange={setNewConversationOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Message</DialogTitle>
          </DialogHeader>
          <UserPicker value={recipient} onChange={setRecipient} placeholder="Search for a member..." />
          <Button
            disabled={!recipient}
            onClick={() => recipient && router.push(`/messaging/direct/${recipient.id}`)}
          >
            Start Conversation
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
