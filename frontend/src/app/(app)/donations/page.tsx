"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { HandCoins, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateCampaignDialog } from "@/components/donations/create-campaign-dialog";
import { CampaignDetailDialog } from "@/components/donations/campaign-detail-dialog";
import * as donationsApi from "@/lib/api/donations";
import type { FundraisingCampaign } from "@/lib/api/donations";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";

const STATUS_VARIANT: Record<string, "success" | "outline" | "secondary"> = {
  ACTIVE: "success",
  PLANNING: "outline",
  COMPLETED: "secondary",
  CANCELLED: "outline",
};

export default function DonationsPage() {
  const user = useAuthStore((s) => s.user);
  const canManage = hasPermission(user, "hierarchy.manage");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<FundraisingCampaign | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => donationsApi.listCampaigns(),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Donations</h1>
          <p className="text-sm text-muted-foreground">
            Fundraising campaigns, pledges, and fulfillment tracking
          </p>
        </div>
        {canManage && (
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> New Campaign
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState icon={HandCoins} title="No campaigns yet" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.results.map((campaign) => (
            <Card
              key={campaign.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => setSelectedCampaign(campaign)}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent">
                    <HandCoins className="size-4" />
                  </div>
                  <Badge variant={STATUS_VARIANT[campaign.status] ?? "outline"}>
                    {campaign.status}
                  </Badge>
                </div>
                <p className="mt-3 font-medium">{campaign.title}</p>
                <p className="text-xs text-muted-foreground">{campaign.target_unit.name}</p>
                <p className="mt-2 text-sm font-medium">
                  Goal: GHS {Number(campaign.goal_amount).toLocaleString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateCampaignDialog open={createOpen} onOpenChange={setCreateOpen} />
      <CampaignDetailDialog
        campaign={selectedCampaign}
        open={!!selectedCampaign}
        onOpenChange={(open) => !open && setSelectedCampaign(null)}
      />
    </div>
  );
}
