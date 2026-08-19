"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { ClipboardCheck, Loader2, Send } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { UserPicker } from "@/components/shared/user-picker";
import { EmptyState } from "@/components/shared/empty-state";
import * as directivesApi from "@/lib/api/directives";
import { ApiError } from "@/lib/api/client";

const STATUS_VARIANT: Record<string, "success" | "warning" | "outline"> = {
  COMPLETED: "success",
  ACKNOWLEDGED: "warning",
  PENDING: "outline",
};

function textareaClassName() {
  return "flex min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50";
}

export function AssignDirectivePanel() {
  const queryClient = useQueryClient();
  const [assignee, setAssignee] = useState<{ id: string; full_name: string } | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");

  const { data: issued, isLoading } = useQuery({
    queryKey: ["issued-directives"],
    queryFn: () => directivesApi.fetchIssuedDirectives(),
  });

  const assignMutation = useMutation({
    mutationFn: () =>
      directivesApi.assignDirective({
        assigned_to_id: assignee!.id,
        title,
        description: description || undefined,
        due_at: dueDate ? new Date(dueDate).toISOString() : undefined,
      }),
    onSuccess: () => {
      toast.success("Directive assigned.");
      setAssignee(null);
      setTitle("");
      setDescription("");
      setDueDate("");
      queryClient.invalidateQueries({ queryKey: ["issued-directives"] });
    },
    onError: (error: ApiError) =>
      toast.error(error.message || "Could not assign directive."),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ClipboardCheck className="size-4 text-primary" />
          Assign a Directive
        </CardTitle>
        <CardDescription>
          Send a task directly to any National, Regional, or Constituency/District executive.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label>Assign to</Label>
          <UserPicker
            value={assignee}
            onChange={setAssignee}
            placeholder="Search for an executive..."
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Title</Label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Prepare the region for the campaign launch"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Details (optional)</Label>
          <textarea
            className={textareaClassName()}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Any additional context or instructions."
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Due date (optional)</Label>
          <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </div>
        <Button
          onClick={() => assignMutation.mutate()}
          disabled={!assignee || !title || assignMutation.isPending}
          className="w-fit"
        >
          {assignMutation.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Send className="size-4" />
          )}
          Assign Directive
        </Button>

        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">Directives you&apos;ve issued</p>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : !issued || issued.results.length === 0 ? (
            <EmptyState icon={ClipboardCheck} title="No directives issued yet" compact />
          ) : (
            <div className="flex flex-col gap-2">
              {issued.results.map((directive) => (
                <div key={directive.id} className="flex items-center justify-between text-sm">
                  <div>
                    <p className="font-medium">{directive.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {directive.assigned_to.full_name}
                      {directive.assigned_to.organizational_unit
                        ? ` · ${directive.assigned_to.organizational_unit}`
                        : ""}
                      {" · "}
                      {format(new Date(directive.created_at), "MMM d, yyyy")}
                    </p>
                  </div>
                  <Badge variant={STATUS_VARIANT[directive.status] ?? "outline"}>
                    {directive.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
