"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import * as hierarchyApi from "@/lib/api/hierarchy";
import { unitTypeLabel } from "@/lib/api/hierarchy";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export function UnitPicker({
  value,
  onChange,
  placeholder = "Select a unit...",
  unitType,
  disabled,
}: {
  value: { id: string; name: string } | null;
  onChange: (unit: { id: string; name: string } | null) => void;
  placeholder?: string;
  /** Restrict results to one unit_type (e.g. only BRANCH units for a transfer target). */
  unitType?: string;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 300);

  const { data, isLoading } = useQuery({
    queryKey: ["unit-picker", debouncedQuery, unitType],
    queryFn: () =>
      hierarchyApi.listUnits({ search: debouncedQuery || undefined, unit_type: unitType, page: 1 }),
    enabled: open,
  });

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          disabled={disabled}
          className="w-full justify-between font-normal"
        >
          <span className={cn("truncate", !value && "text-muted-foreground")}>
            {value ? value.name : placeholder}
          </span>
          <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0">
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <Search className="size-3.5 shrink-0 text-muted-foreground" />
          <Input
            autoFocus
            placeholder="Search units..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-7 border-none px-0 shadow-none focus-visible:ring-0"
          />
        </div>
        <ScrollArea className="h-64">
          {isLoading ? (
            <p className="p-4 text-center text-sm text-muted-foreground">Searching...</p>
          ) : !data || data.results.length === 0 ? (
            <p className="p-4 text-center text-sm text-muted-foreground">No units found.</p>
          ) : (
            <div className="p-1">
              {data.results.map((unit) => (
                <button
                  key={unit.id}
                  onClick={() => {
                    onChange({ id: unit.id, name: unit.name });
                    setOpen(false);
                  }}
                  className="flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-secondary"
                >
                  <div className="min-w-0">
                    <p className="truncate">{unit.name}</p>
                    <p className="text-xs text-muted-foreground">{unitTypeLabel(unit.unit_type)}</p>
                  </div>
                  {value?.id === unit.id && <Check className="size-4 shrink-0 text-primary" />}
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
