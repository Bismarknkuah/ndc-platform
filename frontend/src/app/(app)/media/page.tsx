"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { FileAudio, Film, Image as ImageIcon, Newspaper, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/shared/empty-state";
import { UploadMediaDialog } from "@/components/media/upload-media-dialog";
import * as mediaApi from "@/lib/api/media";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

const TYPE_ICON: Record<string, React.ElementType> = {
  PHOTO: ImageIcon,
  VIDEO: Film,
  AUDIO: FileAudio,
  PRESS_CLIPPING: Newspaper,
  OTHER: ImageIcon,
};

function MediaDetailDialog({
  assetId,
  open,
  onOpenChange,
}: {
  assetId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: asset, isLoading } = useQuery({
    queryKey: ["media-asset", assetId],
    queryFn: () => mediaApi.getMediaAsset(assetId!),
    enabled: !!assetId && open,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {isLoading || !asset ? (
          <Skeleton className="h-48" />
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>{asset.title}</DialogTitle>
              <DialogDescription>{asset.organizational_unit.name}</DialogDescription>
            </DialogHeader>
            {asset.media_type === "PHOTO" && asset.file_base64 && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`data:image/jpeg;base64,${asset.file_base64}`}
                alt={asset.title}
                className="w-full rounded-lg object-cover"
              />
            )}
            {asset.external_url && (
              <a
                href={asset.external_url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-primary underline"
              >
                Open external media →
              </a>
            )}
            {asset.description && <p className="text-sm text-muted-foreground">{asset.description}</p>}
            {asset.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {asset.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function MediaPage() {
  const user = useAuthStore((s) => s.user);
  const canManage = hasPermission(user, "hierarchy.manage");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["media"],
    queryFn: () => mediaApi.listMedia(),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Media Library</h1>
          <p className="text-sm text-muted-foreground">Photos, videos, audio, and press clippings</p>
        </div>
        {canManage && (
          <Button onClick={() => setUploadOpen(true)}>
            <Plus /> Add Media
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={ImageIcon} title="No media yet" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {data.results.map((asset) => {
            const Icon = TYPE_ICON[asset.media_type] ?? ImageIcon;
            return (
              <Card
                key={asset.id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => setSelectedId(asset.id)}
              >
                <CardContent className="pt-6">
                  <div className="flex size-10 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
                    <Icon className="size-5" />
                  </div>
                  <p className="mt-3 truncate font-medium">{asset.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {format(new Date(asset.created_at), "MMM d, yyyy")}
                  </p>
                  {asset.tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {asset.tags.slice(0, 2).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-[10px]">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <UploadMediaDialog open={uploadOpen} onOpenChange={setUploadOpen} />
      <MediaDetailDialog
        assetId={selectedId}
        open={!!selectedId}
        onOpenChange={(open) => !open && setSelectedId(null)}
      />
    </div>
  );
}
