"use client";

import { useState } from "react";
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
  const [showMap, setShowMap] = useState(false);
  const visible = showMap || selectedStop !== null;
  return (
    <section className={`map-panel${visible ? "" : " map-collapsed"}`} aria-label="Route map">
      {visible ? <><div className="map-toolbar">
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
      <RouteMap plan={plan} selectedStop={selectedStop} /></> : (
        <div className="map-opt-in">
          <span className="map-preview-line" aria-hidden="true">A ───── B</span>
          <h2>Your journey at a glance</h2>
          <p>The fuel plan is ready below. Load the interactive map when you need it.</p>
          <button type="button" className="secondary-button" onClick={() => setShowMap(true)}>Load route map</button>
          <small>Uses additional map data</small>
        </div>
      )}
    </section>
  );
}
