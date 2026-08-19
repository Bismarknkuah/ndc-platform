"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { MessageSquareWarning, Plus, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateComplaintDialog } from "@/components/complaints/create-complaint-dialog";
import { ComplaintDetailDialog } from "@/components/complaints/complaint-detail-dialog";
import * as complaintsApi from "@/lib/api/complaints";
import type { Complaint } from "@/lib/api/complaints";

const STATUS_VARIANT: Record<string, "success" | "warning" | "outline" | "secondary"> = {
  RESOLVED: "success",
  UNDER_REVIEW: "warning",
  SUBMITTED: "outline",
  DISMISSED: "secondary",
};

export default function ComplaintsPage() {
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["complaints", typeFilter],
    queryFn: () =>
      complaintsApi.listComplaints(
        typeFilter === "all" ? undefined : { complaint_type: typeFilter },
      ),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Complaints & Petitions</h1>
          <p className="text-sm text-muted-foreground">
            Addressed upward to your own unit or any ancestor of it
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus /> File New
        </Button>
      </div>

      <Select value={typeFilter} onValueChange={setTypeFilter}>
        <SelectTrigger size="sm" className="w-48">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="COMPLAINT">Complaints</SelectItem>
          <SelectItem value="PETITION">Petitions</SelectItem>
        </SelectContent>
      </Select>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={MessageSquareWarning} title="Nothing filed yet" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((complaint) => (
            <Card
              key={complaint.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => setSelectedComplaint(complaint)}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{complaint.subject}</p>
                      {complaint.complaint_type === "PETITION" && (
                        <Badge variant="outline">
                          <Users className="size-3" /> Petition
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">
                      {complaint.description}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {complaint.submitting_unit.name} → {complaint.target_unit.name} ·{" "}
                      {format(new Date(complaint.created_at), "MMM d, yyyy")}
                    </p>
                  </div>
                  <Badge variant={STATUS_VARIANT[complaint.status] ?? "outline"}>
                    {complaint.status.replace("_", " ")}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateComplaintDialog open={createOpen} onOpenChange={setCreateOpen} />
      <ComplaintDetailDialog
        complaint={selectedComplaint}
        open={!!selectedComplaint}
        onOpenChange={(open) => !open && setSelectedComplaint(null)}
      />
    </div>
  );
}
