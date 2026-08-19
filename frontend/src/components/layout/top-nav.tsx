"use client";

import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetHeader } from "@/components/ui/sheet";
import { Breadcrumbs } from "./breadcrumbs";
import { SidebarNav } from "./sidebar";
import { NotificationBell } from "./notification-bell";
import { UserMenu } from "./user-menu";
import { ThemeSwitcher } from "./theme-switcher";
import { useState } from "react";

export function TopNav() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

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

      <div className="ml-auto flex items-center gap-1">
        <ThemeSwitcher />
        <NotificationBell />
        <div className="mx-1 h-5 w-px bg-border" />
        <UserMenu />
      </div>
    </header>
  );
}
