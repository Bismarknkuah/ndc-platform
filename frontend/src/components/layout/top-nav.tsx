"use client";

import { Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetHeader } from "@/components/ui/sheet";
import { Breadcrumbs } from "./breadcrumbs";
import { SidebarNav } from "./sidebar";
import { NotificationBell } from "./notification-bell";
import { UserMenu } from "./user-menu";
import { ThemeSwitcher } from "./theme-switcher";
import { LanguageSwitcher } from "./language-switcher";
import { useCommandPaletteStore } from "@/stores/command-palette-store";
import { useState } from "react";

export function TopNav() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const setCommandPaletteOpen = useCommandPaletteStore((s) => s.setOpen);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-surface/95 px-4 backdrop-blur supports-backdrop-filter:bg-surface/75">
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation</SheetTitle>
          </SheetHeader>
          <SidebarNav onNavigate={() => setMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={() => setMobileNavOpen(true)}
        aria-label="Open navigation"
      >
        <Menu className="size-4" />
      </Button>

      <div className="hidden lg:block">
        <Breadcrumbs />
      </div>

      <button
        onClick={() => setCommandPaletteOpen(true)}
        className="ml-auto flex h-8 w-full max-w-sm items-center gap-2 rounded-md border border-input bg-secondary/50 px-3 text-sm text-muted-foreground transition-colors hover:bg-secondary lg:ml-4"
      >
        <Search className="size-3.5" />
        <span className="hidden sm:inline">Search or run a command...</span>
        <span className="ml-auto hidden items-center gap-0.5 text-xs sm:flex">
          <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">
            ⌘
          </kbd>
          <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">
            K
          </kbd>
        </span>
      </button>

      <div className="ml-auto flex items-center gap-1 lg:ml-0">
        <LanguageSwitcher />
        <ThemeSwitcher />
        <NotificationBell />
        <div className="mx-1 h-5 w-px bg-border" />
        <UserMenu />
      </div>
    </header>
  );
}
