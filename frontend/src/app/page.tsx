"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { HomepageContent } from "@/components/homepage/homepage-content";

export default function RootPage() {
  const { status, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, router]);

  // Still resolving auth state, or about to redirect - avoid a flash of
  // the public homepage for someone who's actually already signed in.
  if (status === "unknown" || isAuthenticated) {
    return <div className="h-dvh bg-background" />;
  }

  return <HomepageContent />;
}
