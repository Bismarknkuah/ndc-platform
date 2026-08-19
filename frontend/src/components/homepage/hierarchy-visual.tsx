"use client";

const TIERS = [
  { label: "National", detail: "One party, one direction" },
  { label: "Regional", detail: "Sixteen regions, one voice" },
  { label: "Constituency", detail: "Where elections are won" },
  { label: "Branch", detail: "Every member starts here" },
];

export function HierarchyVisual() {
  return (
    <div className="flex flex-col gap-3" aria-label="NDC constitutional hierarchy, Branch to National">
      {TIERS.map((tier, index) => {
        const widthPercent = 100 - index * 16;
        return (
          <div key={tier.label} className="flex items-center gap-4">
            <div
              className="flex h-14 items-center justify-between rounded-lg border border-primary/20 bg-primary/[0.04] px-5 transition-all"
              style={{ width: `${widthPercent}%` }}
            >
              <span className="font-display font-semibold text-foreground">{tier.label}</span>
              <span className="hidden text-xs text-muted-foreground sm:block">{tier.detail}</span>
            </div>
          </div>
        );
      })}
      <p className="mt-1 text-xs text-muted-foreground">
        Article 11 of the NDC Constitution. The four levels this platform is built around.
      </p>
    </div>
  );
}
