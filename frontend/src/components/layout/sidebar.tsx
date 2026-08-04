"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { NAV_SECTIONS } from "@/lib/nav-config";
import { canSeeNavItem } from "@/lib/permissions";
import { useAuthStore } from "@/stores/auth-store";
import { ScrollArea } from "@/components/ui/scroll-area";

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex h-14 items-center gap-2.5 px-4">
        <div className="relative flex size-8 shrink-0 items-center justify-center">
          <Image src="/ndc-logo.png" alt="NDC" fill sizes="32px" className="object-contain" priority />
        </div>
        <div className="flex flex-col leading-none">
          <span className="font-display text-sm font-semibold">NDC</span>
          <span className="text-[11px] text-sidebar-foreground/60">Party Platform</span>
        </div>
      </div>

      <ScrollArea className="flex-1 px-2">
        <nav className="flex flex-col gap-4 py-2 pb-6">
          {NAV_SECTIONS.map((section) => {
            const visibleItems = section.items.filter((item) => canSeeNavItem(user, item));
            if (visibleItems.length === 0) return null;

            return (
              <div key={section.title}>
                <p className="px-3 pb-1.5 text-[11px] font-medium tracking-wide text-sidebar-foreground/45 uppercase">
                  {section.title}
                </p>
                <div className="flex flex-col gap-0.5">
                  {visibleItems.map((item) => {
                    const active =
                      pathname === item.href || pathname.startsWith(`${item.href}/`);
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={onNavigate}
                        className={cn(
                          "group flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                          active
                            ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                            : "text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                        )}
                      >
                        <item.icon
                          className={cn(
                            "size-4 shrink-0",
                            active ? "text-sidebar-primary" : "opacity-70",
                          )}
                        />
                        <span className="truncate">{item.title}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>
      </ScrollArea>
    </div>
  );
}
