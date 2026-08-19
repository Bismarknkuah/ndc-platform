"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/shared/empty-state";
import { MessageBubble } from "@/components/chat/message-bubble";
import { ChatComposer } from "@/components/chat/chat-composer";
import * as dmApi from "@/lib/api/direct-messages";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";

export default function DirectMessageConversationPage() {
  const params = useParams<{ userId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const { data, isLoading } = useQuery({
    queryKey: ["direct-messages", "conversation", params.userId],
    queryFn: () => dmApi.listDirectMessages(params.userId),
    refetchInterval: 8000,
  });

  const sendMutation = useMutation({
    mutationFn: (body: string) => dmApi.sendDirectMessage(params.userId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["direct-messages"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not send message."),
  });

  const markReadMutation = useMutation({
    mutationFn: (messageId: string) => dmApi.markDirectMessageRead(messageId),
  });

  const messages = [...(data?.results ?? [])].reverse();
  const otherUser = messages.find((m) => m.sender.id !== user?.id)?.sender ?? messages[0]?.recipient;

  // Mark any unread incoming messages in this thread as read once loaded.
  useEffect(() => {
    if (!data || !user) return;
    for (const message of data.results) {
      if (message.recipient.id === user.id && message.read_at === null) {
        markReadMutation.mutate(message.id);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, user]);

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="border-b border-border pb-3">
        <Button variant="ghost" size="sm" onClick={() => router.push("/messaging/direct")}>
          ← Back to Messages
        </Button>
        <h1 className="mt-1 text-lg font-display font-semibold">
          {otherUser?.full_name ?? "Conversation"}
        </h1>
      </div>

      <ScrollArea className="flex-1 py-4">
        {isLoading ? (
          <Skeleton className="h-full" />
        ) : messages.length === 0 ? (
          <EmptyState
            icon={Mail}
            title="No messages yet"
            description="Send the first message to start this conversation."
            compact
          />
        ) : (
          <div className="flex flex-col gap-3 px-1">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                body={message.body}
                senderName={message.sender.full_name}
                createdAt={message.created_at}
                isOwn={message.sender.id === user?.id}
              />
            ))}
          </div>
        )}
      </ScrollArea>

      <ChatComposer onSend={(body) => sendMutation.mutate(body)} disabled={sendMutation.isPending} />
      {sendMutation.isPending && (
        <p className="flex items-center gap-1 px-1 pt-1 text-xs text-muted-foreground">
          <Loader2 className="size-3 animate-spin" /> Sending...
        </p>
      )}
    </div>
  );
}
