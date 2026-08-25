"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Copy, Loader2, Monitor, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { UnitPicker } from "@/components/shared/unit-picker";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import * as kioskApi from "@/lib/api/kiosk";
import { ApiError } from "@/lib/api/client";

export function KiosksTab({ electionId }: { electionId: string }) {
  const queryClient = useQueryClient();
  const [registerOpen, setRegisterOpen] = useState(false);
  const [unit, setUnit] = useState<{ id: string; name: string } | null>(null);
  const [label, setLabel] = useState("");
  const [newKioskCode, setNewKioskCode] = useState<string | null>(null);

  const { data: kiosks, isLoading } = useQuery({
    queryKey: ["kiosks", electionId],
    queryFn: () => kioskApi.listKiosks(electionId),
  });

  const registerMutation = useMutation({
    mutationFn: () => kioskApi.registerKiosk(electionId, unit!.id, label),
    onSuccess: (kiosk) => {
      setNewKioskCode(kiosk.kiosk_code ?? null);
      queryClient.invalidateQueries({ queryKey: ["kiosks", electionId] });
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not register kiosk."),
  });

  function closeDialog() {
    setRegisterOpen(false);
    setUnit(null);
    setLabel("");
    setNewKioskCode(null);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Physical walk-up voting terminals for this election. Each kiosk shows its code exactly
          once, at registration - write it down or hand it to the polling official immediately.
        </p>
        <Button onClick={() => setRegisterOpen(true)}>
          <Plus className="size-4" /> Register Kiosk
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : !kiosks || kiosks.length === 0 ? (
        <EmptyState icon={Monitor} title="No kiosks registered yet" />
      ) : (
        <div className="flex flex-col gap-2">
          {kiosks.map((kiosk) => (
            <div
              key={kiosk.id}
              className="flex items-center justify-between rounded-lg border p-3"
            >
              <div>
                <p className="text-sm font-medium">{kiosk.label}</p>
                <p className="text-xs text-muted-foreground">{kiosk.unit.name}</p>
              </div>
              <Badge variant={kiosk.is_active ? "success" : "outline"}>
                {kiosk.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
          ))}
        </div>
      )}

      <Dialog open={registerOpen} onOpenChange={(v) => !v && closeDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Register a Kiosk</DialogTitle>
            <DialogDescription>
              This identifies a real, physical voting terminal - not a secret by itself. Voter
              security comes from each member&apos;s own Kiosk PIN, set in their account.
            </DialogDescription>
          </DialogHeader>

          {newKioskCode ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm">
                Kiosk registered. This code will not be shown again - record it now.
              </p>
              <div className="flex items-center gap-2 rounded-md border bg-muted/30 p-3 font-mono text-sm">
                {newKioskCode}
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-auto"
                  onClick={() => {
                    navigator.clipboard.writeText(newKioskCode);
                    toast.success("Copied.");
                  }}
                >
                  <Copy className="size-3.5" />
                </Button>
              </div>
              <DialogFooter>
                <Button onClick={closeDialog}>Done</Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <Label>Unit</Label>
                <UnitPicker value={unit} onChange={setUnit} placeholder="Select a unit..." />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Label</Label>
                <Input
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="e.g. Branch 023 - Community Center"
                />
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={closeDialog}>
                  Cancel
                </Button>
                <Button
                  onClick={() => registerMutation.mutate()}
                  disabled={!unit || !label || registerMutation.isPending}
                >
                  {registerMutation.isPending && <Loader2 className="size-4 animate-spin" />}
                  Register
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
