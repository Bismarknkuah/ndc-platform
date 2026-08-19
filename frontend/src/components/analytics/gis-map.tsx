"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";
import type { GeoJSONFeature } from "@/lib/api/analytics";

const LeafletMap = dynamic(() => import("./leaflet-map"), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

export function GISMap({ features }: { features: GeoJSONFeature[] }) {
  return (
    <div className="h-[500px] w-full overflow-hidden rounded-lg border border-border">
      <LeafletMap features={features} />
    </div>
  );
}
