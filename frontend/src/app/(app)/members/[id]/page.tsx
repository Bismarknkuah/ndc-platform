"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeftRight,
  Ban,
  CheckCircle2,
  Mail,
  MapPin,
  Phone,
  ShieldCheck,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/error-state";
import { OrgUnitPathLinks } from "@/components/layout/org-unit-path";
import { TransferMemberDialog } from "@/components/members/transfer-member-dialog";
import { SuspendMemberDialog } from "@/components/members/suspend-member-dialog";
import * as membersApi from "@/lib/api/members";
import * as hierarchyApi from "@/lib/api/hierarchy";

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm">{value || "—"}</p>
    </div>
  );
}

export default function MemberDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [transferOpen, setTransferOpen] = useState(false);
  const [suspendOpen, setSuspendOpen] = useState(false);

  const {
    data: member,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["member", params.id],
    queryFn: () => membersApi.getMember(params.id),
  });

  const { data: ancestors } = useQuery({
    queryKey: ["unit-ancestors", member?.organizational_unit?.id],
    queryFn: () => hierarchyApi.getUnitAncestors(member!.organizational_unit!.id),
    enabled: !!member?.organizational_unit,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (isError || !member) {
    return <ErrorState title="Couldn't load this member" onRetry={() => refetch()} />;
  }

  const orgPath = [...(ancestors ?? []), member.organizational_unit].filter(
    (u): u is NonNullable<typeof u> => !!u,
  );

  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" size="sm" className="w-fit" onClick={() => router.push("/members")}>
        ← Back to Members
      </Button>

      {orgPath.length > 0 && <OrgUnitPathLinks units={orgPath} />}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <Avatar className="size-16">
            <AvatarFallback className="text-lg">
              {member.first_name.charAt(0)}
              {member.last_name.charAt(0)}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-display font-semibold">{member.full_name}</h1>
              <Badge variant={member.is_active ? "success" : "destructive"}>
                {member.is_active ? "Active" : "Suspended"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {member.role?.name ?? "Ordinary Member"} · {member.membership_id}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setTransferOpen(true)}>
            <ArrowLeftRight /> Transfer
          </Button>
          <Button
            variant={member.is_active ? "destructive" : "default"}
            onClick={() => setSuspendOpen(true)}
          >
            {member.is_active ? <Ban /> : <CheckCircle2 />}
            {member.is_active ? "Suspend" : "Reactivate"}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Personal Information</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-x-6 divide-y divide-border [&>*:nth-last-child(-n+2)]:border-0">
            <DetailRow label="Gender" value={member.gender} />
            <DetailRow
              label="Date of birth"
              value={
                member.date_of_birth ? new Date(member.date_of_birth).toLocaleDateString() : null
              }
            />
            <DetailRow label="Ghana Card number" value={member.national_id_number} />
            <DetailRow label="Voter ID" value={member.voter_id_number} />
            <DetailRow label="Occupation" value={member.occupation} />
            <DetailRow label="Marital status" value={member.marital_status} />
            <DetailRow label="Residential address" value={member.residential_address} />
            <DetailRow label="Emergency contact" value={member.emergency_contact_name} />
            <DetailRow label="Emergency phone" value={member.emergency_contact_phone} />
            <DetailRow
              label="Joined"
              value={new Date(member.date_joined).toLocaleDateString()}
            />
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Contact</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="flex items-center gap-2 text-sm">
                <Mail className="size-4 text-muted-foreground" />
                {member.email}
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Phone className="size-4 text-muted-foreground" />
                {member.phone_number}
              </div>
              {member.organizational_unit && (
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="size-4 text-muted-foreground" />
                  {member.organizational_unit.name}
                </div>
              )}
            </CardContent>
          </Card>

          {member.role && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Position</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <ShieldCheck className="size-4 text-primary" />
                  {member.role.name}
                </div>
                <div className="flex flex-wrap gap-1">
                  {member.role.permissions.map((permission) => (
                    <Badge key={permission} variant="outline" className="font-mono text-[10px]">
                      {permission}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <TransferMemberDialog
        memberId={member.id}
        memberName={member.full_name}
        open={transferOpen}
        onOpenChange={setTransferOpen}
      />
      <SuspendMemberDialog
        memberId={member.id}
        memberName={member.full_name}
        isCurrentlyActive={member.is_active}
        open={suspendOpen}
        onOpenChange={setSuspendOpen}
      />
    </div>
  );
}
