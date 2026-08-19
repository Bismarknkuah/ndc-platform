"use client";

import Link from "next/link";
import Image from "next/image";
import {
  FileText,
  Vote,
  Wallet,
  Gavel,
  Bot,
  MessageSquare,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { HierarchyVisual } from "./hierarchy-visual";

const FEATURES = [
  {
    icon: FileText,
    title: "Paperless by design",
    description:
      "Membership records, meeting minutes, complaints, and disciplinary hearings. All digital, all traceable, nothing lost to a filing cabinet.",
  },
  {
    icon: Vote,
    title: "Elections & voting",
    description:
      "From branch collation to national results, run internal elections the constitution actually describes, end to end.",
  },
  {
    icon: Wallet,
    title: "Dues, made simple",
    description:
      "Members pay directly from their phone: Mobile Money, bank transfer, or card. No more chasing paper receipts.",
  },
  {
    icon: Gavel,
    title: "Disciplinary Committee",
    description:
      "Articles 46–47's actual timelines and appeal process, built into the workflow itself, not left to memory.",
  },
  {
    icon: Bot,
    title: "An assistant for executives",
    description:
      "Draft a broadcast, summarize a backlog, plan a meeting agenda. A second pair of hands for the officers carrying the most.",
  },
  {
    icon: MessageSquare,
    title: "One party, in sync",
    description:
      "Broadcasts and reports move up and down the real chain of command, Branch to National, the way the constitution intends.",
  },
];

export function HomepageContent() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-20 -right-20 opacity-[0.04]"
        >
          <Image src="/ndc-logo.png" alt="" width={480} height={520} priority={false} />
        </div>
        <div className="mx-auto flex max-w-6xl flex-col gap-10 px-6 py-16 sm:py-24 lg:flex-row lg:items-center">
          <div className="flex-1">
            <div className="mb-6 flex items-center gap-3">
              <div className="relative size-11">
                <Image src="/ndc-logo.png" alt="NDC" fill sizes="44px" className="object-contain" priority />
              </div>
              <span className="text-sm font-medium tracking-wide text-muted-foreground">
                NATIONAL DEMOCRATIC CONGRESS
              </span>
            </div>
            <h1 className="max-w-xl font-display text-4xl font-semibold leading-tight text-foreground sm:text-5xl">
              The party&apos;s business, run the way the constitution describes it.
            </h1>
            <p className="mt-5 max-w-lg text-base text-muted-foreground sm:text-lg">
              One platform for every level of the party, from a Branch Secretary registering a
              new member to the National Executive Committee reviewing the whole organization at
              once. Built directly from the NDC Constitution, Article by Article.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link href="/login">
                  Sign in <ArrowRight className="size-4" />
                </Link>
              </Button>
              <span className="text-xs text-muted-foreground">
                Unity, Stability and Development
              </span>
            </div>
          </div>

          <div className="flex-1">
            <Card className="border-primary/10 bg-card/60 backdrop-blur-sm">
              <CardContent className="pt-6">
                <HierarchyVisual />
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-16 sm:py-20">
        <div className="mb-10 max-w-lg">
          <h2 className="font-display text-2xl font-semibold text-foreground sm:text-3xl">
            Everything a party this size actually runs on
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            Not a generic tool adapted to fit. Built for this constitution, this structure, this
            party.
          </p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <div key={feature.title} className="rounded-lg border border-border bg-card p-5">
              <div className="mb-3 flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <feature.icon className="size-5" />
              </div>
              <h3 className="font-display font-semibold text-foreground">{feature.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-6 py-10 text-center">
          <div className="flex h-1.5 w-24 overflow-hidden rounded-full">
            <div className="flex-1 bg-[#1a1a1a]" />
            <div className="flex-1 bg-destructive" />
            <div className="flex-1 bg-[#f7f8f7] dark:bg-white" />
            <div className="flex-1 bg-primary" />
          </div>
          <p className="text-sm text-muted-foreground">
            National Democratic Congress. Unity, Stability and Development
          </p>
          <Button asChild variant="outline" size="sm">
            <Link href="/login">Member sign in</Link>
          </Button>
        </div>
      </footer>
    </div>
  );
}
