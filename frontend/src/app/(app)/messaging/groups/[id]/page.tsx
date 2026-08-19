"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, MessagesSquare, Settings, UserMinus, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { UserPicker } from "@/components/shared/user-picker";
import { EmptyState } from "@/components/shared/empty-state";
import { MessageBubble } from "@/components/chat/message-bubble";
import { ChatComposer } from "@/components/chat/chat-composer";
import * as groupsApi from "@/lib/api/groups";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";

export default function GroupChatPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [addingMember, setAddingMember] = useState(false);
  const [newMember, setNewMember] = useState<{ id: string; full_name: string } | null>(null);

  const { data: groupsPage } = useQuery({
    queryKey: ["groups"],
    queryFn: () => groupsApi.listGroups(),
  });
  const group = groupsPage?.results.find((g) => g.id === params.id);
  const isOwner = group?.created_by.id === user?.id;

  const { data: messagesPage, isLoading } = useQuery({
    queryKey: ["group-messages", params.id],
    queryFn: () => groupsApi.listGroupMessages(params.id),
    refetchInterval: 8000,
  });

  const sendMutation = useMutation({
    mutationFn: (body: string) => groupsApi.sendGroupMessage(params.id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["group-messages", params.id] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not send message."),
  });

  const addMemberMutation = useMutation({
    mutationFn: (userId: string) => groupsApi.addGroupMember(params.id, userId),
    onSuccess: () => {
      toast.success("Member added.");
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      setNewMember(null);
      setAddingMember(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not add member."),
  });

  const removeMemberMutation = useMutation({
    mutationFn: (userId: string) => groupsApi.removeGroupMember(params.id, userId),
    onSuccess: () => {
      toast.success("Member removed.");
      queryClient.invalidateQueries({ queryKey: ["groups"] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not remove member."),
  });

  // Messages come back newest-first from the API; a chat thread reads
  // oldest-to-newest top-to-bottom.
  const messages = [...(messagesPage?.results ?? [])].reverse();

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <Button variant="ghost" size="sm" onClick={() => router.push("/messaging/groups")}>
            ← Back to Groups
          </Button>
          <h1 className="mt-1 text-lg font-display font-semibold">{group?.name ?? "Group"}</h1>
        </div>
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" size="icon">
              <Settings className="size-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-72">
            <p className="mb-2 text-sm font-medium">Members ({group?.members.length ?? 0})</p>
            <ul className="mb-3 flex max-h-48 flex-col gap-1 overflow-y-auto">
              {group?.members.map((member) => (
                <li key={member.id} className="flex items-center justify-between text-sm">
                  <span>{member.full_name}</span>
                  {isOwner && member.id !== user?.id && (
                    <button
                      onClick={() => removeMemberMutation.mutate(member.id)}
                      className="text-destructive hover:opacity-70"
                    >
                      <UserMinus className="size-3.5" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {isOwner &&
              (addingMember ? (
                <div className="flex flex-col gap-2">
                  <UserPicker value={newMember} onChange={setNewMember} />
                  <Button
                    size="sm"
                    disabled={!newMember || addMemberMutation.isPending}
                    onClick={() => newMember && addMemberMutation.mutate(newMember.id)}
                  >
                    Add
                  </Button>
                </div>
              ) : (
                <Button size="sm" variant="outline" onClick={() => setAddingMember(true)}>
                  <UserPlus className="size-3.5" /> Add Member
                </Button>
              ))}
          </PopoverContent>
        </Popover>
      </div>

      <ScrollArea className="flex-1 py-4">
        {isLoading ? (
          <Skeleton className="h-full" />
        ) : messages.length === 0 ? (
          <EmptyState icon={MessagesSquare} title="No messages yet" description="Say hello!" compact />
        ) : (
          <div className="flex flex-col gap-3 px-1">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                body={message.body}
                senderName={message.sender.full_name}
                createdAt={message.created_at}
                isOwn={message.sender.id === user?.id}
                showSenderName
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
