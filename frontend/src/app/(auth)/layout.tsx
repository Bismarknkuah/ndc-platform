"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { FileText, Gavel, Vote, Wallet } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

const HIGHLIGHTS = [
  { icon: FileText, text: "Every record, digital and traceable" },
  { icon: Vote, text: "Branch-to-national election collation" },
  { icon: Wallet, text: "Dues by Mobile Money, bank, or card" },
  { icon: Gavel, text: "Disciplinary Committee, built to the Constitution" },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { status, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, router]);

  if (status === "unknown" || isAuthenticated) {
    return <div className="h-dvh bg-background" />;
  }

  return (
    <div className="relative flex min-h-dvh overflow-hidden bg-background">
      {/* Brand panel - hidden on small screens, where the form alone is
          the whole experience. */}
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden bg-sidebar px-12 py-12 text-sidebar-foreground lg:flex">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -bottom-24 opacity-[0.06]"
        >
          <Image src="/ndc-logo.png" alt="" width={520} height={560} priority={false} />
        </div>

        <div className="relative z-10 flex items-center gap-3">
          <div className="relative size-9">
            <Image src="/ndc-logo.png" alt="NDC" fill sizes="36px" className="object-contain" priority />
          </div>
          <span className="text-sm font-medium tracking-wide opacity-80">
            NATIONAL DEMOCRATIC CONGRESS
          </span>
        </div>

        <div className="relative z-10 max-w-md">
          <h1 className="font-display text-3xl font-semibold leading-tight">
            The party&apos;s business, run the way the constitution describes it.
          </h1>
          <div className="mt-8 flex flex-col gap-4">
            {HIGHLIGHTS.map((item) => (
              <div key={item.text} className="flex items-center gap-3">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-sidebar-accent">
                  <item.icon className="size-4" />
                </div>
                <span className="text-sm opacity-90">{item.text}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-xs opacity-60">Unity, Stability and Development</p>
      </div>

      {/* Form panel */}
      <div className="relative flex flex-1 items-center justify-center px-4 py-12">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -bottom-24 opacity-[0.05] dark:opacity-[0.07] lg:hidden"
        >
          <Image src="/ndc-logo.png" alt="" width={560} height={600} priority={false} />
        </div>
        <div className="relative z-10 w-full max-w-sm">{children}</div>
      </div>
    </div>
  );
}
