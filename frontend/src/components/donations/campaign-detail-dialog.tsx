"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { HandCoins, Loader2, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import { UserPicker } from "@/components/shared/user-picker";
import * as donationsApi from "@/lib/api/donations";
import type { FundraisingCampaign } from "@/lib/api/donations";
import { ApiError } from "@/lib/api/client";

export function CampaignDetailDialog({
  campaign,
  open,
  onOpenChange,
}: {
  campaign: FundraisingCampaign | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [addingPledge, setAddingPledge] = useState(false);
  const [donorUser, setDonorUser] = useState<{ id: string; full_name: string } | null>(null);
  const [donorName, setDonorName] = useState("");
  const [pledgeAmount, setPledgeAmount] = useState("");
  const [fulfillingId, setFulfillingId] = useState<string | null>(null);
  const [fulfillAmount, setFulfillAmount] = useState("");

  const { data: progress } = useQuery({
    queryKey: ["campaign-progress", campaign?.id],
    queryFn: () => donationsApi.getCampaignProgress(campaign!.id),
    enabled: !!campaign && open,
  });

  const { data: pledges } = useQuery({
    queryKey: ["pledges", campaign?.id],
    queryFn: () => donationsApi.listPledges(campaign!.id),
    enabled: !!campaign && open,
  });

  const recordMutation = useMutation({
    mutationFn: () =>
      donationsApi.recordPledge({
        campaign_id: campaign!.id,
        donor_user_id: donorUser?.id,
        donor_name: donorUser ? undefined : donorName || undefined,
        pledged_amount: pledgeAmount,
      }),
    onSuccess: () => {
      toast.success("Pledge recorded.");
      queryClient.invalidateQueries({ queryKey: ["pledges", campaign?.id] });
      queryClient.invalidateQueries({ queryKey: ["campaign-progress", campaign?.id] });
      setAddingPledge(false);
      setDonorUser(null);
      setDonorName("");
      setPledgeAmount("");
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not record pledge."),
  });

  const fulfillMutation = useMutation({
    mutationFn: (pledgeId: string) => donationsApi.fulfillPledge(pledgeId, fulfillAmount),
    onSuccess: () => {
      toast.success("Payment recorded. A finance record was created automatically.");
      queryClient.invalidateQueries({ queryKey: ["pledges", campaign?.id] });
      queryClient.invalidateQueries({ queryKey: ["campaign-progress", campaign?.id] });
      setFulfillingId(null);
      setFulfillAmount("");
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not record payment."),
  });

  if (!campaign) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{campaign.title}</DialogTitle>
          <DialogDescription>{campaign.target_unit.name}</DialogDescription>
        </DialogHeader>

        {progress && (
          <div className="flex flex-col gap-2">
            <div className="flex justify-between text-sm">
              <span>GHS {Number(progress.total_fulfilled).toLocaleString()} raised</span>
              <span className="text-muted-foreground">
                of GHS {Number(progress.goal_amount).toLocaleString()} goal
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{
                  width: `${Math.min(progress.percentage_of_goal_fulfilled, 100)}%`,
                }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {progress.percentage_of_goal_fulfilled}% of goal · {progress.pledge_count} pledges ·
              GHS {Number(progress.total_pledged).toLocaleString()} pledged total
            </p>
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border pt-3">
          <p className="text-sm font-medium">Pledges</p>
          <Button size="sm" variant="outline" onClick={() => setAddingPledge(true)}>
            <Plus className="size-3.5" /> Record Pledge
          </Button>
        </div>

        {addingPledge && (
          <div className="flex flex-col gap-3 rounded-lg border border-border p-3">
            <div className="flex flex-col gap-1.5">
              <Label>Donor (member, optional)</Label>
              <UserPicker value={donorUser} onChange={setDonorUser} />
            </div>
            {!donorUser && (
              <div className="flex flex-col gap-1.5">
                <Label>Or donor name</Label>
                <Input value={donorName} onChange={(e) => setDonorName(e.target.value)} />
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <Label>Pledged amount (GHS)</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={pledgeAmount}
                onChange={(e) => setPledgeAmount(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => setAddingPledge(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => recordMutation.mutate()}
                disabled={!pledgeAmount || recordMutation.isPending}
              >
                {recordMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
                Save
              </Button>
            </div>
          </div>
        )}

        {!pledges || pledges.results.length === 0 ? (
          <EmptyState icon={HandCoins} title="No pledges yet" compact />
        ) : (
          <ul className="flex flex-col gap-2">
            {pledges.results.map((pledge) => (
              <li key={pledge.id} className="rounded-lg border border-border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{pledge.donor_display_name}</span>
                  <Badge variant={pledge.status === "FULFILLED" ? "success" : "outline"}>
                    {pledge.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  GHS {Number(pledge.fulfilled_amount).toLocaleString()} of{" "}
                  {Number(pledge.pledged_amount).toLocaleString()} fulfilled
                </p>
                {pledge.status !== "FULFILLED" && pledge.status !== "CANCELLED" && (
                  <>
                    {fulfillingId === pledge.id ? (
                      <div className="mt-2 flex items-center gap-2">
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          className="h-8"
                          placeholder="Amount received"
                          value={fulfillAmount}
                          onChange={(e) => setFulfillAmount(e.target.value)}
                        />
                        <Button
                          size="sm"
                          onClick={() => fulfillMutation.mutate(pledge.id)}
                          disabled={!fulfillAmount || fulfillMutation.isPending}
                        >
                          Save
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setFulfillingId(null)}>
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="link"
                        className="mt-1 h-auto p-0"
                        onClick={() => setFulfillingId(pledge.id)}
                      >
                        Record payment received
                      </Button>
                    )}
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}
