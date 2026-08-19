"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { MessagesSquare, Plus, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateGroupDialog } from "@/components/groups/create-group-dialog";
import * as groupsApi from "@/lib/api/groups";

export default function GroupsListPage() {
  const router = useRouter();
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["groups"],
    queryFn: () => groupsApi.listGroups(),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Discussion Groups</h1>
          <p className="text-sm text-muted-foreground">Groups you belong to or created</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus /> New Group
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={MessagesSquare} title="No groups yet" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.results.map((group) => (
            <Card
              key={group.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/messaging/groups/${group.id}`)}
            >
              <CardContent className="pt-6">
                <p className="font-medium">{group.name}</p>
                {group.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                    {group.description}
                  </p>
                )}
                <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                  <Users className="size-3" /> {group.members.length} members
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateGroupDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
