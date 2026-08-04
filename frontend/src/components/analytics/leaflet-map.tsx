"use client";

import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import Link from "next/link";
import type { GeoJSONFeature } from "@/lib/api/analytics";

const UNIT_TYPE_COLOR: Record<string, string> = {
  NATIONAL: "#0e6b3e",
  REGIONAL: "#1a8f56",
  CONSTITUENCY: "#b8860b",
  DISTRICT_COORDINATING_COMMITTEE: "#2f6690",
  BRANCH: "#c8352e",
};

function colorFor(unitType: string): string {
  return UNIT_TYPE_COLOR[unitType] ?? "#5b6560";
}

export default function LeafletMap({ features }: { features: GeoJSONFeature[] }) {
  // Default center: mean of all points, falling back to Ghana's
  // approximate centroid if nothing has coordinates yet.
  const center: [number, number] =
    features.length > 0
      ? [
          features.reduce((sum, f) => sum + f.geometry.coordinates[1], 0) / features.length,
          features.reduce((sum, f) => sum + f.geometry.coordinates[0], 0) / features.length,
        ]
      : [7.9465, -1.0232];

  return (
    <MapContainer
      center={center}
      zoom={features.length > 0 ? 8 : 6}
      scrollWheelZoom
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {features.map((feature) => (
        <CircleMarker
          key={feature.properties.id}
          center={[feature.geometry.coordinates[1], feature.geometry.coordinates[0]]}
          radius={8}
          pathOptions={{
            color: colorFor(feature.properties.unit_type),
            fillColor: colorFor(feature.properties.unit_type),
            fillOpacity: 0.7,
            weight: 2,
          }}
        >
          <Popup>
            <div className="text-sm">
              <p className="font-medium">{feature.properties.name}</p>
              <p className="text-xs text-muted-foreground">
                {feature.properties.unit_type.replace("_", " ")}
              </p>
              <Link
                href={`/hierarchy/${feature.properties.id}`}
                className="text-xs text-primary underline"
              >
                View unit →
              </Link>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
