"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import * as rolesApi from "@/lib/api/roles";

export function RolePicker({
  value,
  onChange,
  excludeId,
  placeholder = "None (top-level position)",
}: {
  value: { id: string; name: string } | null;
  onChange: (role: { id: string; name: string } | null) => void;
  /** Exclude a role from the list - e.g. a role can't report to itself. */
  excludeId?: string;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: () => rolesApi.listRoles(),
    enabled: open,
  });

  const filtered = (roles ?? []).filter((r) => r.id !== excludeId);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" className="w-full justify-between font-normal">
          <span className={cn("truncate", !value && "text-muted-foreground")}>
            {value ? value.name : placeholder}
          </span>
          <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-0">
        <ScrollArea className="h-64">
          <div className="p-1">
            <button
              onClick={() => {
                onChange(null);
                setOpen(false);
              }}
              className="flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-secondary"
            >
              <span className="text-muted-foreground">None (top-level position)</span>
              {!value && <Check className="size-4 shrink-0 text-primary" />}
            </button>
            {filtered.map((role) => (
              <button
                key={role.id}
                onClick={() => {
                  onChange({ id: role.id, name: role.name });
                  setOpen(false);
                }}
                className="flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-secondary"
              >
                <div className="min-w-0">
                  <p className="truncate">{role.name}</p>
                  <p className="text-xs text-muted-foreground">{role.scope}</p>
                </div>
                {value?.id === role.id && <Check className="size-4 shrink-0 text-primary" />}
              </button>
            ))}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
