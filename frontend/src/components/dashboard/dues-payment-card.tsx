"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { format } from "date-fns";
import { Loader2, Receipt } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import * as duesApi from "@/lib/api/dues";
import { ApiError } from "@/lib/api/client";

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "outline"> = {
  SUCCESS: "success",
  PENDING: "warning",
  FAILED: "destructive",
  ABANDONED: "outline",
};

export function DuesPaymentCard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState("");

  const { data: history, isLoading } = useQuery({
    queryKey: ["dues-history"],
    queryFn: () => duesApi.fetchDuesHistory(),
  });

  const initializeMutation = useMutation({
    mutationFn: () => duesApi.initializeDuesPayment(amount),
    onSuccess: (result) => {
      window.location.href = result.authorization_url;
    },
    onError: (error: ApiError) => toast.error(error.message || "Could not start payment."),
  });

  // Returning from Paystack's checkout: Paystack appends ?reference=...
  // to the callback_url we gave it - verify it explicitly rather than
  // waiting on the webhook alone.
  useEffect(() => {
    const reference = searchParams.get("reference");
    if (!reference) return;

    duesApi
      .verifyDuesPayment(reference)
      .then((payment) => {
        if (payment.status === "SUCCESS") {
          toast.success("Payment received - thank you!");
        } else if (payment.status === "PENDING") {
          toast.info("Payment is still processing - check back shortly.");
        } else {
          toast.error("Payment was not completed.");
        }
        queryClient.invalidateQueries({ queryKey: ["dues-history"] });
        router.replace("/dashboard");
      })
      .catch(() => {
        toast.error("Could not confirm payment status.");
      });
    // Only run once on mount for whatever reference is in the URL.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Receipt className="size-4 text-primary" />
          Membership Dues
        </CardTitle>
        <CardDescription>
          Pay via Mobile Money (MTN and others), bank transfer, or card.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-end gap-2">
          <div className="flex flex-1 flex-col gap-1.5">
            <Label>Amount (GHS)</Label>
            <Input
              type="number"
              min="1"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="e.g. 20.00"
            />
          </div>
          <Button
            onClick={() => initializeMutation.mutate()}
            disabled={!amount || Number(amount) <= 0 || initializeMutation.isPending}
          >
            {initializeMutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Pay Now
          </Button>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">Recent payments</p>
          {isLoading ? (
            <Skeleton className="h-16" />
          ) : !history || history.results.length === 0 ? (
            <EmptyState icon={Receipt} title="No payments yet" compact />
          ) : (
            <div className="flex flex-col gap-2">
              {history.results.slice(0, 5).map((payment) => (
                <div key={payment.id} className="flex items-center justify-between text-sm">
                  <div>
                    <p className="font-medium">
                      GHS {payment.amount} · {payment.period}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {format(new Date(payment.created_at), "MMM d, yyyy")}
                      {payment.payment_method && ` · ${payment.payment_method.replace(/_/g, " ")}`}
                    </p>
                  </div>
                  <Badge variant={STATUS_VARIANT[payment.status] ?? "outline"}>
                    {payment.status}
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
