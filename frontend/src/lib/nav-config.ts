import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Users,
  Network,
  Building2,
  MessagesSquare,
  Vote,
  CalendarDays,
  Wallet,
  HeartHandshake,
  MessageSquareWarning,
  Gavel,
  FileText,
  HandCoins,
  UsersRound,
  BarChart3,
  Image as ImageIcon,
  Settings,
  Shield,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  /** Permission tag required to see this item; omit for "any authenticated user". */
  permission?: string;
  /** Alternative: visible if the user holds ANY of these tags (OR logic). */
  anyPermissions?: string[];
  description?: string;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    title: "Overview",
    items: [
      {
        title: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
        description: "Your role-adaptive home screen",
      },
    ],
  },
  {
    title: "Organization",
    items: [
      {
        title: "Hierarchy",
        href: "/hierarchy",
        icon: Network,
        description: "National, Regional, Constituency, Branch",
      },
      {
        title: "Members",
        href: "/members",
        icon: Users,
        anyPermissions: ["hierarchy.manage", "membership.register"],
        description: "Search, provision, suspend, transfer members",
      },
      {
        title: "Departments",
        href: "/departments",
        icon: Building2,
        description: "Departmental chain of command, tasks, dashboards",
      },
    ],
  },
  {
    title: "Engagement",
    items: [
      {
        title: "Messaging",
        href: "/messaging",
        icon: MessagesSquare,
        description: "Broadcasts, reports, groups, meetings, direct messages",
      },
      {
        title: "Elections",
        href: "/elections",
        icon: Vote,
        description: "Internal elections, polls, and general election collation",
      },
      {
        title: "Events & Campaigns",
        href: "/events",
        icon: CalendarDays,
      },
      {
        title: "Volunteers",
        href: "/volunteers",
        icon: UsersRound,
      },
    ],
  },
  {
    title: "Operations",
    items: [
      {
        title: "Finance",
        href: "/finance",
        icon: Wallet,
        permission: "finance.view",
      },
      {
        title: "Donations",
        href: "/donations",
        icon: HandCoins,
        permission: "finance.view",
      },
      {
        title: "Welfare",
        href: "/welfare",
        icon: HeartHandshake,
      },
      {
        title: "Complaints & Petitions",
        href: "/complaints",
        icon: MessageSquareWarning,
      },
      {
        title: "Discipline",
        href: "/discipline",
        icon: Gavel,
        description: "Articles 46-47: Disciplinary Committees, cases, suspensions",
      },
      {
        title: "Documents",
        href: "/documents",
        icon: FileText,
      },
      {
        title: "Media Library",
        href: "/media",
        icon: ImageIcon,
      },
    ],
  },
  {
    title: "Insights",
    items: [
      {
        title: "Analytics",
        href: "/analytics",
        icon: BarChart3,
        permission: "hierarchy.manage",
      },
    ],
  },
  {
    title: "Administration",
    items: [
      {
        title: "Position Management",
        href: "/settings/positions",
        icon: Shield,
        permission: "hierarchy.manage_roles",
        description: "Create, rename, and configure party positions",
      },
      {
        title: "Settings",
        href: "/settings",
        icon: Settings,
      },
    ],
  },
];

export const ALL_NAV_ITEMS: NavItem[] = NAV_SECTIONS.flatMap((section) => section.items);
