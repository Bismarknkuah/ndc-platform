"use client";

import { useEffect, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { LogOut, Moon, Sun, UserRound } from "lucide-react";
import { useTheme } from "next-themes";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { ALL_NAV_ITEMS } from "@/lib/nav-config";
import { canSeeNavItem, hasPermission } from "@/lib/permissions";
import { useAuthStore } from "@/stores/auth-store";
import { useAuth } from "@/hooks/use-auth";
import * as membersApi from "@/lib/api/members";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useCommandPaletteStore } from "@/stores/command-palette-store";

export function CommandPalette() {
  const open = useCommandPaletteStore((s) => s.open);
  const setOpen = useCommandPaletteStore((s) => s.setOpen);
  const toggle = useCommandPaletteStore((s) => s.toggle);
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 300);
  const router = useRouter();
  const { setTheme } = useTheme();
  const { logout } = useAuth();
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        toggle();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [toggle]);

  const canSearchMembers = hasPermission(user, "hierarchy.manage") || hasPermission(user, "membership.register");

  const { data: memberResults } = useQuery({
    queryKey: ["command-palette", "members", debouncedQuery],
    queryFn: () => membersApi.listMembers({ search: debouncedQuery, page: 1 }),
    enabled: open && canSearchMembers && debouncedQuery.length >= 2,
  });

  const runCommand = useCallback(
    (action: () => void) => {
      setOpen(false);
      action();
    },
    [setOpen],
  );

  const visibleNavItems = ALL_NAV_ITEMS.filter((item) => canSeeNavItem(user, item));

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search pages, members, or run a command..." value={query} onValueChange={setQuery} />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {debouncedQuery.length < 2 && (
          <CommandGroup heading="Navigate">
            {visibleNavItems.map((item) => (
              <CommandItem
                key={item.href}
                onSelect={() => runCommand(() => router.push(item.href))}
              >
                <item.icon />
                {item.title}
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {canSearchMembers && memberResults && memberResults.results.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Members">
              {memberResults.results.slice(0, 6).map((member) => (
                <CommandItem
                  key={member.id}
                  onSelect={() => runCommand(() => router.push(`/members/${member.id}`))}
                >
                  <UserRound />
                  <span>{member.full_name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {member.membership_id}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        {debouncedQuery.length < 2 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Actions">
              <CommandItem onSelect={() => runCommand(() => setTheme("light"))}>
                <Sun /> Switch to light theme
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => setTheme("dark"))}>
                <Moon /> Switch to dark theme
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => router.push("/profile"))}>
                <UserRound /> View profile
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => logout())}>
                <LogOut /> Log out
              </CommandItem>
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
