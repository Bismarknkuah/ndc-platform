"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { format } from "date-fns";
import { Download, FileText, Loader2, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { UploadDocumentDialog } from "@/components/documents/upload-document-dialog";
import * as documentsApi from "@/lib/api/documents";
import { myAssignments } from "@/lib/api/departments";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

function DownloadButton({ documentId, fileName }: { documentId: string; fileName: string }) {
  const [downloading, setDownloading] = useState(false);

  async function handleDownload() {
    setDownloading(true);
    try {
      const doc = await documentsApi.getDocument(documentId);
      const link = window.document.createElement("a");
      link.href = `data:${doc.mime_type};base64,${doc.file_base64}`;
      link.download = fileName;
      link.click();
    } catch {
      toast.error("Could not download this document.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Button size="sm" variant="outline" onClick={handleDownload} disabled={downloading}>
      {downloading ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" />}
      Download
    </Button>
  );
}

export default function DocumentsPage() {
  const user = useAuthStore((s) => s.user);
  const hasHierarchyAuthority = hasPermission(user, "hierarchy.manage");

  // can_manage_documents on the backend also grants authority to a
  // HEAD/DEPUTY_HEAD of any department (not just Communications, since
  // Documents covers everything from financial reports to legal
  // filings to minutes - genuinely multi-department content, unlike
  // Media which is specifically Communications' job) - worth the extra
  // request to check for real rather than hiding this from department
  // heads who genuinely need it.
  const { data: assignments } = useQuery({
    queryKey: ["my-department-assignments"],
    queryFn: myAssignments,
    enabled: !hasHierarchyAuthority,
  });
  const hasAnyDepartmentAuthority = (assignments ?? []).some(
    (a) => a.is_active && (a.position === "HEAD" || a.position === "DEPUTY_HEAD"),
  );
  const canManage = hasHierarchyAuthority || hasAnyDepartmentAuthority;
  const [uploadOpen, setUploadOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsApi.listDocuments(),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Constitution, minutes, forms, policy, and financial reports
          </p>
        </div>
        {canManage && (
          <Button onClick={() => setUploadOpen(true)}>
            <Plus /> Upload Document
          </Button>
        )}
      </div>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={FileText} title="No documents yet" />
      ) : (
        <div className="flex flex-col gap-3">
          {data.results.map((document) => (
            <Card key={document.id}>
              <CardContent className="flex items-center gap-3 pt-6">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText className="size-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{document.title}</p>
                    <Badge variant="outline">{document.category.replace("_", " ")}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {document.organizational_unit.name} · {document.uploaded_by.full_name} ·{" "}
                    {format(new Date(document.created_at), "MMM d, yyyy")}
                  </p>
                </div>
                <DownloadButton documentId={document.id} fileName={document.file_name} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <UploadDocumentDialog open={uploadOpen} onOpenChange={setUploadOpen} />
    </div>
  );
}
