"use client";

import dynamic from "next/dynamic";
import type { RoutePlan } from "@/lib/types";

const RouteMap = dynamic(
  () =>
    import("@/components/route-planner/RouteMap").then(
      (module) => module.RouteMap,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="map-loading">
        <span className="spinner" aria-hidden="true" />
        Loading map
      </div>
    ),
  },
);

interface MapPanelProps {
  plan: RoutePlan;
  selectedStop: number | null;
}

export function MapPanel({ plan, selectedStop }: MapPanelProps) {
  return (
    <section className="map-panel">
      <div className="map-toolbar">
        <div>
          <span className="legend-line" aria-hidden="true" />
          Route
        </div>
        <div>
          <span className="legend-stop" aria-hidden="true">
            1
          </span>
          Fuel stop
        </div>
      </div>
      <RouteMap plan={plan} selectedStop={selectedStop} />
    </section>
  );
}
