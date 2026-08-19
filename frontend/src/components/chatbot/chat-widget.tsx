"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import {
  Bot,
  History,
  Loader2,
  MessageCircle,
  Plus,
  Sparkles,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/components/chat/message-bubble";
import { ChatComposer } from "@/components/chat/chat-composer";
import { EmptyState } from "@/components/shared/empty-state";
import * as chatbotApi from "@/lib/api/chatbot";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";

const WELCOME_MESSAGE =
  "Hi! I'm the NDC Platform Assistant. Ask me how to do something on the " +
  "platform, or a general question about how the party is organized - " +
  "I'm here 24/7.";

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"chat" | "history">("chat");
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: conversations } = useQuery({
    queryKey: ["chat-conversations"],
    queryFn: () => chatbotApi.listConversations(),
    enabled: open,
  });

  // Opening the widget with existing conversations but none selected yet
  // just needs to default to the most recent one - a derived value, not
  // state that needs syncing via an effect.
  const effectiveConversationId =
    activeConversationId ?? (view === "chat" ? (conversations?.results[0]?.id ?? null) : null);

  const { data: messagesPage, isLoading: messagesLoading } = useQuery({
    queryKey: ["chat-messages", effectiveConversationId],
    queryFn: () => chatbotApi.listMessages(effectiveConversationId!),
    enabled: !!effectiveConversationId,
  });

  const createConversationMutation = useMutation({
    mutationFn: () => chatbotApi.createConversation(),
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ["chat-conversations"] });
      setActiveConversationId(conversation.id);
      setView("chat");
      setUnavailable(false);
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not start a chat."),
  });

  const sendMessageMutation = useMutation({
    mutationFn: (body: string) => chatbotApi.sendMessage(effectiveConversationId!, body),
    onSuccess: () => {
      setUnavailable(false);
      queryClient.invalidateQueries({ queryKey: ["chat-messages", effectiveConversationId] });
      queryClient.invalidateQueries({ queryKey: ["chat-conversations"] });
    },
    onError: (error: ApiError) => {
      if (error.code === "chat_unavailable" || error.status === 503) {
        setUnavailable(true);
        queryClient.invalidateQueries({ queryKey: ["chat-messages", effectiveConversationId] });
      } else {
        toast.error(error.message || "Could not send message.");
      }
    },
  });

  // Open the widget for the first time with zero conversations at all?
  // Auto-start one so there's no empty "pick a conversation" step for a
  // first-time user. This is the one case that genuinely needs an effect
  // (calling the mutation, an external system) rather than a derived
  // value - picking among *existing* conversations is handled above by
  // effectiveConversationId instead, with no setState in an effect.
  const autoCreateAttempted = useRef(false);
  useEffect(() => {
    if (!open || !conversations) return;
    if (conversations.results.length > 0) {
      autoCreateAttempted.current = false;
      return;
    }
    if (autoCreateAttempted.current) return;
    autoCreateAttempted.current = true;
    createConversationMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, conversations]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messagesPage]);

  const messages = messagesPage?.results ?? [];

  return (
    <div className="fixed right-5 bottom-5 z-40">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 12 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 bottom-16 flex h-[520px] w-[380px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-border bg-sidebar px-4 py-3 text-sidebar-foreground">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-full bg-sidebar-primary text-sidebar-primary-foreground">
                  <Bot className="size-4" />
                </div>
                <div>
                  <p className="text-sm font-medium leading-none">NDC Assistant</p>
                  <p className="text-[11px] text-sidebar-foreground/60">Available 24/7</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  onClick={() => setView(view === "chat" ? "history" : "chat")}
                  title="Conversation history"
                >
                  <History className="size-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  onClick={() => createConversationMutation.mutate()}
                  title="New conversation"
                >
                  <Plus className="size-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  onClick={() => setOpen(false)}
                >
                  <X className="size-3.5" />
                </Button>
              </div>
            </div>

            {view === "history" ? (
              <ScrollArea className="flex-1">
                {!conversations || conversations.results.length === 0 ? (
                  <EmptyState icon={MessageCircle} title="No conversations yet" compact />
                ) : (
                  <ul className="divide-y divide-border">
                    {conversations.results.map((conversation) => (
                      <li key={conversation.id}>
                        <button
                          onClick={() => {
                            setActiveConversationId(conversation.id);
                            setView("chat");
                            setUnavailable(false);
                          }}
                          className="w-full px-4 py-3 text-left text-sm hover:bg-secondary/50"
                        >
                          <p className="truncate font-medium">{conversation.title}</p>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </ScrollArea>
            ) : (
              <>
                <ScrollArea className="flex-1 px-3 py-3">
                  <div className="flex flex-col gap-3">
                    <div className="flex items-start gap-2 rounded-lg bg-secondary/60 p-3 text-xs text-muted-foreground">
                      <Sparkles className="mt-0.5 size-3.5 shrink-0 text-primary" />
                      <span>{WELCOME_MESSAGE}</span>
                    </div>
                    {messagesLoading ? (
                      <Loader2 className="mx-auto size-5 animate-spin text-muted-foreground" />
                    ) : (
                      messages.map((message) => (
                        <MessageBubble
                          key={message.id}
                          body={message.body}
                          senderName={
                            message.role === "ASSISTANT"
                              ? "NDC Assistant"
                              : (user?.first_name ?? "You")
                          }
                          createdAt={message.created_at}
                          isOwn={message.role === "USER"}
                        />
                      ))
                    )}
                    {sendMessageMutation.isPending && (
                      <div className="flex items-center gap-1.5 self-start rounded-2xl rounded-bl-sm bg-secondary px-3.5 py-2 text-xs text-muted-foreground">
                        <Loader2 className="size-3 animate-spin" /> Thinking...
                      </div>
                    )}
                    {unavailable && (
                      <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs text-warning">
                        The assistant isn&apos;t available right now (it may not be
                        configured on this deployment). Your message was saved - try
                        again shortly.
                      </div>
                    )}
                    <div ref={scrollRef} />
                  </div>
                </ScrollArea>
                <ChatComposer
                  onSend={(body) => {
                    if (!effectiveConversationId) return;
                    sendMessageMutation.mutate(body);
                  }}
                  disabled={!effectiveConversationId || sendMessageMutation.isPending}
                />
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <Button
        size="icon"
        onClick={() => setOpen((prev) => !prev)}
        className="size-13 rounded-full shadow-lg"
        aria-label={open ? "Close assistant" : "Open assistant"}
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={open ? "close" : "open"}
            initial={{ opacity: 0, rotate: -45 }}
            animate={{ opacity: 1, rotate: 0 }}
            exit={{ opacity: 0, rotate: 45 }}
            transition={{ duration: 0.15 }}
            className="flex items-center justify-center"
          >
            {open ? <X className="size-5" /> : <Bot className="size-5" />}
          </motion.span>
        </AnimatePresence>
      </Button>
    </div>
  );
}
