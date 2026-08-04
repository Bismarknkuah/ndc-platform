"use client";

import {
  Briefcase,
  Building2,
  Landmark,
  MapPin,
  Megaphone,
  Network,
  ShieldAlert,
  User,
  UserCheck,
  Users,
  Vote,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export interface DemoAccount {
  label: string;
  email: string;
  icon: React.ElementType;
  group: "hierarchy" | "department";
}

// Matches apps/core/management/commands/seed_platform.py's
// _seed_demo_accounts exactly - same emails, same shared password.
// Deliberately visible on the public login page - a product decision
// made with the risk understood (see the seed command's docstring),
// not an oversight. If DEMO_ACCOUNTS_PASSWORD is ever changed on the
// backend away from the default below, update it here too.
//
// Superadmin is listed first and visually distinguished (ShieldAlert
// icon) since it's a materially larger exposure than the rest - a
// genuine is_superadmin=True account that bypasses every permission
// check platform-wide, not just its own Role's permission list.
// "hierarchy" group follows the real constitutional chain (Article 11:
// National -> Regional -> Constituency -> Branch) with District
// Co-ordinating Committee placed where Article 17 actually puts it -
// coordinating constituencies within a region, not a rung between
// Regional and Constituency. "department" group demonstrates the
// department-based dashboard differentiation - each department head
// sees a dashboard tailored to their own department's real work.
export const DEMO_ACCOUNTS: DemoAccount[] = [
  { label: "Superadmin", email: "demo.superadmin@ndc.example", icon: ShieldAlert, group: "hierarchy" },
  { label: "National Chairman", email: "demo.national@ndc.example", icon: Landmark, group: "hierarchy" },
  { label: "Regional Chairman", email: "demo.regional@ndc.example", icon: Building2, group: "hierarchy" },
  { label: "District Co-ordinator", email: "demo.district@ndc.example", icon: Network, group: "hierarchy" },
  { label: "Constituency Chairman", email: "demo.constituency@ndc.example", icon: MapPin, group: "hierarchy" },
  { label: "Branch Secretary", email: "demo.branch@ndc.example", icon: Users, group: "hierarchy" },
  { label: "Ordinary Member", email: "demo.member@ndc.example", icon: User, group: "hierarchy" },
  { label: "Communications Director", email: "demo.comms@ndc.example", icon: Megaphone, group: "department" },
  { label: "National Treasurer", email: "demo.treasurer@ndc.example", icon: Wallet, group: "department" },
  { label: "Elections Director", email: "demo.elections@ndc.example", icon: Vote, group: "department" },
  { label: "Membership Officer", email: "demo.membership@ndc.example", icon: UserCheck, group: "department" },
  { label: "Women's Affairs Director", email: "demo.women@ndc.example", icon: Briefcase, group: "department" },
];

export const DEMO_ACCOUNTS_PASSWORD = "DemoPass123!";

function DemoButton({
  account,
  onSelect,
  disabled,
}: {
  account: DemoAccount;
  onSelect: (account: DemoAccount) => void;
  disabled?: boolean;
}) {
  const isSuperadmin = account.label === "Superadmin";
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className={
        isSuperadmin
          ? "justify-start border-warning/40 text-warning hover:bg-warning/10"
          : "justify-start"
      }
      disabled={disabled}
      onClick={() => onSelect(account)}
    >
      <account.icon className={isSuperadmin ? "size-3.5" : "size-3.5 text-muted-foreground"} />
      {account.label}
    </Button>
  );
}

function GroupDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-px flex-1 bg-border" />
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}

export function DemoLoginButtons({
  onSelect,
  disabled,
}: {
  onSelect: (account: DemoAccount) => void;
  disabled?: boolean;
}) {
  const hierarchyAccounts = DEMO_ACCOUNTS.filter((a) => a.group === "hierarchy");
  const departmentAccounts = DEMO_ACCOUNTS.filter((a) => a.group === "department");

  return (
    <div className="flex flex-col gap-3">
      <GroupDivider label="Try a demo account, by hierarchy" />
      <div className="grid grid-cols-1 gap-1.5">
        {hierarchyAccounts.map((account) => (
          <DemoButton key={account.email} account={account} onSelect={onSelect} disabled={disabled} />
        ))}
      </div>

      <GroupDivider label="Or by department" />
      <div className="grid grid-cols-1 gap-1.5">
        {departmentAccounts.map((account) => (
          <DemoButton key={account.email} account={account} onSelect={onSelect} disabled={disabled} />
        ))}
      </div>
    </div>
  );
}
