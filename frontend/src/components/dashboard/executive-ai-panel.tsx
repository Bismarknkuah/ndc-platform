"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Bot, Copy, Loader2, Megaphone, ClipboardList, CalendarClock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import * as executiveAiApi from "@/lib/api/executive-ai";
import type { AiResponseSource } from "@/lib/api/executive-ai";
import type { JurisdictionSummary } from "@/lib/api/dashboard";
import { ApiError } from "@/lib/api/client";

interface AiResult {
  text: string;
  source: AiResponseSource;
}

function SourceBadge({ source }: { source: AiResponseSource }) {
  return source === "ai" ? (
    <Badge variant="outline" className="text-xs">
      AI Generated
    </Badge>
  ) : (
    <Badge variant="secondary" className="text-xs">
      Data Summary (AI unavailable)
    </Badge>
  );
}

function ResultView({ result }: { result: AiResult }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <SourceBadge source={result.source} />
      </div>
      <div className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
        {result.text}
      </div>
      <Button
        variant="outline"
        size="sm"
        className="w-fit"
        onClick={() => {
          navigator.clipboard.writeText(result.text);
          toast.success("Copied to clipboard.");
        }}
      >
        <Copy className="size-3.5" /> Copy
      </Button>
    </div>
  );
}

function DraftBroadcastDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [topic, setTopic] = useState("");
  const [result, setResult] = useState<AiResult | null>(null);

  const mutation = useMutation({
    mutationFn: () => executiveAiApi.draftBroadcast(topic),
    onSuccess: setResult,
    onError: (error: ApiError) => toast.error(error.message || "Could not draft broadcast."),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v);
        if (!v) {
          setTopic("");
          setResult(null);
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Draft a Broadcast</DialogTitle>
          <DialogDescription>
            Generates a ready-to-edit draft. Nothing is sent automatically. Review and send it
            yourself from Messaging → Broadcasts.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Topic / brief</Label>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Reminder about Saturday's membership drive"
            />
          </div>
          {result && <ResultView result={result} />}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={!topic || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            {result ? "Regenerate" : "Generate Draft"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MeetingAgendaDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [topic, setTopic] = useState("");
  const [result, setResult] = useState<AiResult | null>(null);

  const mutation = useMutation({
    mutationFn: () => executiveAiApi.generateMeetingAgenda(topic),
    onSuccess: setResult,
    onError: (error: ApiError) => toast.error(error.message || "Could not generate agenda."),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v);
        if (!v) {
          setTopic("");
          setResult(null);
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Generate a Meeting Agenda</DialogTitle>
          <DialogDescription>
            A starting point to refine before you actually schedule the meeting.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Meeting topic</Label>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Quarterly budget review"
            />
          </div>
          {result && <ResultView result={result} />}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={!topic || mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            {result ? "Regenerate" : "Generate Agenda"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SummarizePendingDialog({
  open,
  onOpenChange,
  jurisdictionSummary,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  jurisdictionSummary: JurisdictionSummary;
}) {
  const [result, setResult] = useState<AiResult | null>(null);

  const mutation = useMutation({
    mutationFn: () => executiveAiApi.summarizePendingItems(jurisdictionSummary),
    onSuccess: setResult,
    onError: (error: ApiError) => toast.error(error.message || "Could not summarize."),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v);
        if (!v) setResult(null);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Summarize Pending Items</DialogTitle>
          <DialogDescription>
            Based on the {jurisdictionSummary.requires_attention} pending item(s) across your
            jurisdiction right now.
          </DialogDescription>
        </DialogHeader>
        {result ? (
          <ResultView result={result} />
        ) : (
          <p className="text-sm text-muted-foreground">
            Click Generate to get a prioritized summary of what needs attention.
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            {result ? "Regenerate" : "Generate Summary"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ExecutiveAiPanel({
  jurisdictionSummary,
}: {
  jurisdictionSummary?: JurisdictionSummary;
}) {
  const [openDialog, setOpenDialog] = useState<"broadcast" | "agenda" | "summarize" | null>(null);

  const tools = [
    {
      key: "broadcast" as const,
      icon: Megaphone,
      title: "Draft a Broadcast",
      description: "Generate a ready-to-edit broadcast message.",
      disabled: false,
    },
    {
      key: "summarize" as const,
      icon: ClipboardList,
      title: "Summarize Pending Items",
      description: "A prioritized view of what needs your attention.",
      disabled: !jurisdictionSummary,
    },
    {
      key: "agenda" as const,
      icon: CalendarClock,
      title: "Meeting Agenda",
      description: "Draft a structured agenda from a topic.",
      disabled: false,
    },
  ];

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Bot className="size-4 text-primary" />
          Executive AI Assistant
        </CardTitle>
        <CardDescription>
          Drafts and suggestions to review before you act. Nothing here is sent or saved
          automatically. Falls back to a real data-driven summary if AI isn&apos;t configured.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {tools.map((tool) => (
          <button
            key={tool.key}
            onClick={() => setOpenDialog(tool.key)}
            disabled={tool.disabled}
            className="flex flex-col items-start gap-2 rounded-lg border p-3 text-left transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            <tool.icon className="size-5 text-primary" />
            <div>
              <p className="text-sm font-medium">{tool.title}</p>
              <p className="text-xs text-muted-foreground">{tool.description}</p>
            </div>
          </button>
        ))}
      </CardContent>

      <DraftBroadcastDialog
        open={openDialog === "broadcast"}
        onOpenChange={(v) => setOpenDialog(v ? "broadcast" : null)}
      />
      <MeetingAgendaDialog
        open={openDialog === "agenda"}
        onOpenChange={(v) => setOpenDialog(v ? "agenda" : null)}
      />
      {jurisdictionSummary && (
        <SummarizePendingDialog
          open={openDialog === "summarize"}
          onOpenChange={(v) => setOpenDialog(v ? "summarize" : null)}
          jurisdictionSummary={jurisdictionSummary}
        />
      )}
    </Card>
  );
}
