"use client";

import { useMemo, useState } from "react";
import {
  demoRouteOptions,
  getDemoRoutePlan,
} from "@/lib/demo-routes";
import { formatDuration, formatNumber } from "@/lib/format";
import type { RoutePlan } from "@/lib/types";

interface DemoRoutesProps {
  onSelect: (plan: RoutePlan) => void;
}

export function DemoRoutes({ onSelect }: DemoRoutesProps) {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const visibleRoutes = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    if (!normalizedQuery) {
      return demoRouteOptions;
    }
    return demoRouteOptions.filter((route) =>
      `${route.label} ${route.region}`
        .toLocaleLowerCase()
        .includes(normalizedQuery),
    );
  }, [query]);

  function selectRoute(id: string) {
    const plan = getDemoRoutePlan(id);
    if (!plan) {
      return;
    }
    setSelectedId(id);
    onSelect(plan);
    window.requestAnimationFrame(() => {
      document
        .querySelector(".results")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  return (
    <details className="demo-routes" id="demo-routes">
      <summary>
        <span className="demo-info-icon" aria-hidden="true">
          i
        </span>
        <span>
          <strong>Backend sleeping? Explore bundled demo routes</strong>
          <small>
            25 demo routes examples work without waiting for backend.
          </small>
        </span>
        <span className="demo-chevron" aria-hidden="true">
          +
        </span>
      </summary>

      <div className="demo-routes-content">
        <div className="demo-routes-heading">
          <div>
            <p className="eyebrow">Instant product tour</p>
            <h2>Choose a popular route</h2>
            <p>
              These illustrative snapshots are bundled with the frontend. They
              demonstrate the map, route line, fuel stops, and cost summary
              even when the free backend is inactive.
            </p>
          </div>
          <label className="demo-search">
            <span>Filter routes</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Try Miami, Texas, West Coast..."
            />
          </label>
        </div>

        <div className="demo-route-grid">
          {visibleRoutes.map((route) => (
            <button
              className={`demo-route-card${
                selectedId === route.id ? " demo-route-card-selected" : ""
              }`}
              type="button"
              key={route.id}
              onClick={() => selectRoute(route.id)}
            >
              <span className="demo-route-region">{route.region}</span>
              <strong>{route.label}</strong>
              <span className="demo-route-meta">
                {formatNumber(route.distanceMiles, 0)} mi
                <i aria-hidden="true">·</i>
                {formatDuration(route.durationHours)}
              </span>
              <span className="demo-route-action">
                View demo <span aria-hidden="true">→</span>
              </span>
            </button>
          ))}
        </div>

        {visibleRoutes.length === 0 ? (
          <p className="demo-empty">
            No bundled routes match that search. Try a city or region.
          </p>
        ) : null}

        <p className="demo-disclaimer">
          Demo routes use representative geometry and fuel stops. Submit the
          form above for a live optimized route when the backend is available.
        </p>
      </div>
    </details>
  );
}
