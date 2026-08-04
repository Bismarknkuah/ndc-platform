"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useAuth } from "@/hooks/use-auth";
import { SidebarNav } from "./sidebar";
import { TopNav } from "./top-nav";
import { CommandPalette } from "./command-palette";
import { PageTransition } from "./page-transition";
import { ChatWidget } from "@/components/chatbot/chat-widget";

function FullScreenSplash() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-3 bg-background">
      <div className="relative size-14 animate-pulse">
        <Image src="/ndc-logo.png" alt="NDC" fill sizes="56px" className="object-contain" priority />
      </div>
      <p className="text-sm text-muted-foreground">Loading NDC Party Platform...</p>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { status, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status === "unknown") {
    return <FullScreenSplash />;
  }

  if (!isAuthenticated) {
    // Redirect effect above will fire; render nothing meanwhile to avoid
    // flashing protected content.
    return <FullScreenSplash />;
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <aside className="hidden w-64 shrink-0 lg:block">
        <SidebarNav />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopNav />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <PageTransition>{children}</PageTransition>
          </div>
        </main>
      </div>
      <CommandPalette />
      <ChatWidget />
    </div>
  );
}
