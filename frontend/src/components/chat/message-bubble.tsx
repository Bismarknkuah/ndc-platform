"use client";

import { format } from "date-fns";
import { cn } from "@/lib/utils";

export function MessageBubble({
  body,
  senderName,
  createdAt,
  isOwn,
  showSenderName,
}: {
  body: string;
  senderName: string;
  createdAt: string;
  isOwn: boolean;
  /** Show the sender's name above the bubble - useful in group chats, not needed in 1:1 DMs. */
  showSenderName?: boolean;
}) {
  return (
    <div className={cn("flex flex-col", isOwn ? "items-end" : "items-start")}>
      {showSenderName && !isOwn && (
        <span className="mb-0.5 px-1 text-xs text-muted-foreground">{senderName}</span>
      )}
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap",
          isOwn
            ? "rounded-br-sm bg-primary text-primary-foreground"
            : "rounded-bl-sm bg-secondary text-secondary-foreground",
        )}
      >
        {body}
      </div>
      <span className="mt-0.5 px-1 text-[10px] text-muted-foreground">
        {format(new Date(createdAt), "h:mm a")}
      </span>
    </div>
  );
}
