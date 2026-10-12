"use client";

import type { RoutePlan } from "@/lib/types";

function downloadJson(name: string, value: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url; link.download = name;
  document.body.appendChild(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function PlanActions({ plan }: { plan: RoutePlan }) {
  const warning = "Saved prices are historical. Refresh the route before relying on them.";
  return <div className="plan-actions" aria-label="Save this trip">
    <button type="button" className="secondary-button" onClick={() => downloadJson("fuelup-trip.json", { version: 1, exported_at: new Date().toISOString(), warning, plan })}>Save trip JSON</button>
    <button type="button" className="secondary-button" onClick={() => downloadJson("fuelup-route.geojson", { ...plan.route.geojson, fuelup: { exported_at: new Date().toISOString(), warning, market: plan.market, data_quality: plan.data_quality } })}>Download route GeoJSON</button>
    <button type="button" className="secondary-button" onClick={() => window.print()}>Print plan</button>
  </div>;
}
