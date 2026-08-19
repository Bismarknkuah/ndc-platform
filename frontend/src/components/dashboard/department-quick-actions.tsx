"use client";

import Link from "next/link";
import {
  Megaphone,
  Wallet,
  Vote,
  UserPlus,
  Scale,
  Users2,
  Cpu,
  FlaskConical,
  HeartHandshake,
  Landmark,
  Handshake,
  Briefcase,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { TeamLed } from "@/lib/api/dashboard";

interface DepartmentActionConfig {
  icon: React.ElementType;
  description: string;
  actionLabel: string;
  href: string;
}

const DEPARTMENT_ACTIONS: Record<string, DepartmentActionConfig> = {
  communications: {
    icon: Megaphone,
    description: "Keep the party talking with one voice, at every level.",
    actionLabel: "Compose a Broadcast",
    href: "/messaging",
  },
  finance: {
    icon: Wallet,
    description: "Track income, expenses, and dues collected across your unit.",
    actionLabel: "Open Finance",
    href: "/finance",
  },
  elections: {
    icon: Vote,
    description: "Manage candidates, polling agents, and results collation.",
    actionLabel: "Open Elections",
    href: "/elections",
  },
  membership: {
    icon: UserPlus,
    description: "Register new members and keep the roll accurate.",
    actionLabel: "Open Members",
    href: "/members",
  },
  "legal affairs": {
    icon: Scale,
    description: "Complaints, appeals, and constitutional compliance.",
    actionLabel: "Open Complaints",
    href: "/complaints",
  },
  organizing: {
    icon: Users2,
    description: "Grassroots mobilization and organizational structure.",
    actionLabel: "Open Hierarchy",
    href: "/hierarchy",
  },
  "information technology": {
    icon: Cpu,
    description: "Platform operations and the audit trail.",
    actionLabel: "Open Settings",
    href: "/settings",
  },
  "research & innovation": {
    icon: FlaskConical,
    description: "Membership growth, trends, and data-driven strategy.",
    actionLabel: "Open Analytics",
    href: "/analytics",
  },
  "women's affairs": {
    icon: HeartHandshake,
    description: "Women's Wing programs, advocacy, and outreach.",
    actionLabel: "Open Welfare",
    href: "/welfare",
  },
  "youth affairs": {
    icon: HeartHandshake,
    description: "Youth Wing programs and TEIN coordination.",
    actionLabel: "Open Events",
    href: "/events",
  },
  "political committee": {
    icon: Landmark,
    description: "Political strategy and inter-party relations.",
    actionLabel: "Open Messaging",
    href: "/messaging",
  },
  "conflict resolution committee": {
    icon: Handshake,
    description: "Mediating internal disputes before they escalate.",
    actionLabel: "Open Discipline",
    href: "/discipline",
  },
};

const DEFAULT_ACTION: DepartmentActionConfig = {
  icon: Briefcase,
  description: "Your team and its pending work, at a glance.",
  actionLabel: "Open Departments",
  href: "/departments",
};

function getDepartmentAction(departmentName: string): DepartmentActionConfig {
  const key = departmentName.toLowerCase();
  return DEPARTMENT_ACTIONS[key] ?? DEFAULT_ACTION;
}

export function DepartmentQuickActions({ teamsLed }: { teamsLed: TeamLed[] }) {
  if (teamsLed.length === 0) return null;

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {teamsLed.map((team) => {
        const config = getDepartmentAction(team.department.name);
        const officeHref = `/departments/${team.department.id}?unit=${team.organizational_unit.id}`;
        return (
          <Card key={`${team.department.id}-${team.organizational_unit.id}`}>
            <CardHeader className="flex flex-row items-start justify-between pb-3">
              <Link href={officeHref} className="flex items-center gap-2 hover:underline">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <config.icon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm">{team.department.name}</CardTitle>
                  <CardDescription className="text-xs">
                    {team.organizational_unit.name}
                  </CardDescription>
                </div>
              </Link>
              {team.pending_tasks > 0 && (
                <Badge variant="warning">{team.pending_tasks} pending</Badge>
              )}
            </CardHeader>
            <CardContent className="flex flex-col gap-3 pt-0">
              {team.insight.stats.length > 0 && (
                <div className="grid grid-cols-2 gap-2 border-t border-border pt-3 sm:grid-cols-3">
                  {team.insight.stats.map((stat) => (
                    <div key={stat.label}>
                      <p className="font-display text-base font-semibold leading-none">
                        {stat.value}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{stat.label}</p>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex items-center justify-between gap-2">
                <Button asChild size="sm">
                  <Link href={officeHref}>Open Office</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href={config.href}>{config.actionLabel}</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
