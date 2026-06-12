"use client";

import { useState } from "react";
import { FuelStops } from "@/components/route-planner/FuelStops";
import { MapPanel } from "@/components/route-planner/MapPanel";
import { RouteForm } from "@/components/route-planner/RouteForm";
import { TripSummary } from "@/components/route-planner/TripSummary";
import { planRoute } from "@/lib/api";
import type { RoutePlan } from "@/lib/types";

export function RoutePlanner() {
  const [routePlan, setRoutePlan] = useState<RoutePlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handlePlan(start: string, finish: string) {
    setIsLoading(true);
    setError(null);

    try {
      setRoutePlan(await planRoute(start, finish));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to plan this route.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#" aria-label="FuelUp home">
          <span className="brand-mark" aria-hidden="true">
            F
          </span>
          <span>FuelUp</span>
        </a>
        <p className="header-note">
          U.S. routes · 500-mile range · 10 MPG
        </p>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Fuel-aware route planning</p>
          <h1>Go farther. Spend smarter.</h1>
          <p className="hero-intro">
            Map your drive and find practical, cost-effective fuel stops
            without exceeding your vehicle&apos;s range.
          </p>
        </div>
        <RouteForm onSubmit={handlePlan} isLoading={isLoading} />
      </section>

      {error ? (
        <div className="error-banner" role="alert">
          <span className="error-icon" aria-hidden="true">
            !
          </span>
          <div>
            <strong>Route unavailable</strong>
            <p>{error}</p>
          </div>
        </div>
      ) : null}

      {routePlan ? (
        <section className="results" aria-live="polite">
          <TripSummary plan={routePlan} />
          <div className="route-layout">
            <MapPanel plan={routePlan} />
            <FuelStops plan={routePlan} />
          </div>
          <p className="data-note">
            Station positions use approximate city or postal coordinates.
            Prices come from the supplied exercise dataset.
          </p>
        </section>
      ) : (
        <section className="empty-state">
          <div className="empty-route" aria-hidden="true">
            <span />
            <i />
            <span />
          </div>
          <h2>Your route will appear here</h2>
          <p>
            Enter two U.S. locations to see the route, fuel plan, and estimated
            trip cost.
          </p>
        </section>
      )}
    </div>
  );
}

