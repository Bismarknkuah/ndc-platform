"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { Search, UserPlus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DataTable } from "@/components/shared/data-table";
import { PaginationBar } from "@/components/shared/pagination-bar";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import * as membersApi from "@/lib/api/members";
import type { User } from "@/lib/api/types";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useAuthStore } from "@/stores/auth-store";
import { hasAnyPermission } from "@/lib/permissions";
import { ProvisionMemberDialog } from "@/components/members/provision-member-dialog";

function initials(user: User): string {
  return `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`.toUpperCase();
}

export default function MembersPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [provisionOpen, setProvisionOpen] = useState(false);
  const debouncedSearch = useDebouncedValue(search, 300);

  const canView = hasAnyPermission(user, ["hierarchy.manage", "membership.register"]);

  const { data, isLoading } = useQuery({
    queryKey: ["members", debouncedSearch, statusFilter, page],
    queryFn: () =>
      membersApi.listMembers({
        search: debouncedSearch || undefined,
        is_active: statusFilter === "all" ? undefined : statusFilter === "active",
        page,
      }),
    enabled: canView,
  });

  const columns = useMemo<ColumnDef<User>[]>(
    () => [
      {
        header: "Member",
        cell: ({ row }) => {
          const member = row.original;
          return (
            <div className="flex items-center gap-3">
              <Avatar className="size-8">
                <AvatarFallback>{initials(member)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{member.full_name}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {member.membership_id}
                </p>
              </div>
            </div>
          );
        },
      },
      {
        header: "Unit",
        cell: ({ row }) => (
          <span className="text-sm">{row.original.organizational_unit?.name ?? "—"}</span>
        ),
      },
      {
        header: "Role",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.role?.name ?? "Ordinary Member"}
          </span>
        ),
      },
      {
        header: "Status",
        cell: ({ row }) => (
          <Badge variant={row.original.is_active ? "success" : "destructive"}>
            {row.original.is_active ? "Active" : "Suspended"}
          </Badge>
        ),
      },
      {
        header: "Joined",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {new Date(row.original.date_joined).toLocaleDateString()}
          </span>
        ),
      },
    ],
    [],
  );

  if (!canView) {
    return (
      <ForbiddenState description="Browsing the membership directory requires hierarchy or membership-registration authority." />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Members</h1>
          <p className="text-sm text-muted-foreground">
            {data?.count ?? "…"} members in your jurisdiction
          </p>
        </div>
        <Button onClick={() => setProvisionOpen(true)}>
          <UserPlus /> Provision Member
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name, email, or membership ID..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-8"
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger size="sm" className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Suspended</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        isLoading={isLoading}
        emptyTitle="No members found"
        emptyDescription="Try a different search term or filter."
        onRowClick={(member) => router.push(`/members/${member.id}`)}
      />

      {data && (
        <PaginationBar
          currentPage={data.current_page}
          numPages={data.num_pages}
          count={data.count}
          onPageChange={setPage}
        />
      )}

      <ProvisionMemberDialog open={provisionOpen} onOpenChange={setProvisionOpen} />
    </div>
  );
}
