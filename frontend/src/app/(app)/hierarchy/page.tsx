"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { Plus, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DataTable } from "@/components/shared/data-table";
import { PaginationBar } from "@/components/shared/pagination-bar";
import * as hierarchyApi from "@/lib/api/hierarchy";
import { ALL_UNIT_TYPES, unitTypeLabel } from "@/lib/api/hierarchy";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useAuthStore } from "@/stores/auth-store";
import { hasPermission } from "@/lib/permissions";
import { CreateUnitDialog } from "@/components/hierarchy/create-unit-dialog";

export default function HierarchyPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const [search, setSearch] = useState("");
  const [unitType, setUnitType] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const debouncedSearch = useDebouncedValue(search, 300);

  const canManage = hasPermission(user, "hierarchy.manage");

  const { data, isLoading } = useQuery({
    queryKey: ["hierarchy-units", debouncedSearch, unitType, page],
    queryFn: () =>
      hierarchyApi.listUnits({
        search: debouncedSearch || undefined,
        unit_type: unitType === "all" ? undefined : unitType,
        page,
      }),
  });

  const columns = useMemo<ColumnDef<hierarchyApi.OrganizationalUnit>[]>(
    () => [
      {
        header: "Name",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium">{row.original.name}</p>
            <p className="font-mono text-xs text-muted-foreground">{row.original.code}</p>
          </div>
        ),
      },
      {
        header: "Type",
        cell: ({ row }) => <Badge variant="outline">{unitTypeLabel(row.original.unit_type)}</Badge>,
      },
      {
        header: "Parent",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.parent_name ?? "—"}
          </span>
        ),
      },
      {
        header: "Coordinates",
        cell: ({ row }) =>
          row.original.latitude != null ? (
            <span className="font-mono text-xs text-muted-foreground">
              {row.original.latitude.toFixed(3)}, {row.original.longitude?.toFixed(3)}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">Not set</span>
          ),
      },
    ],
    [],
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold">Hierarchy</h1>
          <p className="text-sm text-muted-foreground">
            National, Regional, Constituency, Branch, plus District Co-ordinating
            Committees, TEIN and auxiliary structures
          </p>
        </div>
        {canManage && (
          <Button onClick={() => setCreateOpen(true)}>
            <Plus /> New Unit
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search units..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-8"
          />
        </div>
        <Select
          value={unitType}
          onValueChange={(value) => {
            setUnitType(value);
            setPage(1);
          }}
        >
          <SelectTrigger size="sm" className="w-52">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {ALL_UNIT_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {unitTypeLabel(type)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        isLoading={isLoading}
        emptyTitle="No units found"
        onRowClick={(unit) => router.push(`/hierarchy/${unit.id}`)}
      />

      {data && (
        <PaginationBar
          currentPage={data.current_page}
          numPages={data.num_pages}
          count={data.count}
          onPageChange={setPage}
        />
      )}

      {canManage && (
        <CreateUnitDialog open={createOpen} onOpenChange={setCreateOpen} parent={null} />
      )}
    </div>
  );
}
