"use client";

import { useEffect, useRef, useState } from "react";
import { PlanActions } from "@/components/route-planner/PlanActions";
import { FuelStops } from "@/components/route-planner/FuelStops";
import { MapPanel } from "@/components/route-planner/MapPanel";
import { RouteForm } from "@/components/route-planner/RouteForm";
import { RouteLoading } from "@/components/route-planner/RouteLoading";
import { TripSummary } from "@/components/route-planner/TripSummary";
import { planRoute } from "@/lib/api";
import { plannerError } from "@/lib/planner-errors";
import type { RoutePlan, RouteRequest } from "@/lib/types";

interface PlannerError {
  title: string;
  message: string;
}

export function RoutePlanner() {
  const [routePlan, setRoutePlan] = useState<RoutePlan | null>(null);
  const [error, setError] = useState<PlannerError | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingSeconds, setLoadingSeconds] = useState(0);
  const [activeRoute, setActiveRoute] = useState({
    source: "Ahmedabad, Gujarat",
    destination: "Vadodara, Gujarat",
  });
  const [selectedStop, setSelectedStop] = useState<number | null>(null);
  const requestVersion = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);

  function cancelPlanning() {
    requestVersion.current += 1;
    activeRequest.current?.abort();
    activeRequest.current = null;
    setIsLoading(false);
  }

  useEffect(() => () => activeRequest.current?.abort(), []);

  async function handlePlan(request: RouteRequest) {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const version = ++requestVersion.current;
    setIsLoading(true);
    setLoadingSeconds(0);
    setActiveRoute({ source: request.start, destination: request.finish });
    setError(null);
    setRoutePlan(null);
    setSelectedStop(null);

    try {
      const plan = await planRoute(request, controller.signal);
      if (requestVersion.current === version) {
        setRoutePlan(plan);
      }
    } catch (requestError) {
      if (requestVersion.current !== version) {
        return;
      }
      setError(plannerError(requestError));
    } finally {
      if (requestVersion.current === version) {
        setIsLoading(false);
      }
    }
  }

  useEffect(() => {
    if (!isLoading) {
      return;
    }
    const interval = window.setInterval(
      () => setLoadingSeconds((seconds) => seconds + 1),
      1_000,
    );
    return () => window.clearInterval(interval);
  }, [isLoading]);

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#" aria-label="FuelUp home">
          <span className="brand-mark" aria-hidden="true">
            F
          </span>
          <span>FuelUp</span>
        </a>
        <span className="header-note">India <span aria-hidden="true">/</span> Road trip planner</span>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">For the road ahead</p>
          <h1>Plan your next drive.</h1>
          <p className="hero-intro">
            Your route, your vehicle, and a sensible plan for fuel along the way.
            Petrol and diesel trips across India, in kilometres and rupees.
          </p>
          <p className="guide-note">Start with your journey. Adjust your vehicle details, then see where to stop and how much to buy.</p>
        </div>
        <RouteForm
          onSubmit={handlePlan}
          isLoading={isLoading}
          loadingSeconds={loadingSeconds}
        />
      </section>

      {error ? (
        <div className="error-banner" role="alert">
          <span className="error-icon" aria-hidden="true">
            !
          </span>
          <div>
            <strong>{error.title}</strong>
            <p>{error.message}</p>
          </div>
        </div>
      ) : null}

      {isLoading ? (
        <div className="loading-wrapper">
          <RouteLoading loadingSeconds={loadingSeconds} source={activeRoute.source} destination={activeRoute.destination} />
          <button type="button" className="secondary-button cancel-button" onClick={cancelPlanning}>Cancel planning</button>
        </div>
      ) : routePlan ? (
        <section className="results" aria-live="polite">
          <TripSummary plan={routePlan} />
          <PlanActions plan={routePlan} />
          <div className="route-layout">
            <MapPanel plan={routePlan} selectedStop={selectedStop} />
            <FuelStops
              plan={routePlan}
              selectedStop={selectedStop}
              onSelectStop={setSelectedStop}
            />
          </div>
          <p className="data-note">
            {routePlan.data_quality.warning} Station data: {" "}
            {routePlan.data_quality.station_snapshot}. Detours are {" "}
            {routePlan.metadata.detour_validation}.
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
            Enter two Indian locations and your vehicle details to see the
            route, fuel plan, price confidence, and estimated trip cost.
          </p>
        </section>
      )}

      <footer className="site-footer">
        <p>
          Developed with{" "}
          <span role="img" aria-label="love">
            ❤️
          </span>{" "}
          by Smit Joshi
        </p>
        <a
          href="https://github.com/smitzo"
          target="_blank"
          rel="noreferrer"
          aria-label="Smit Joshi on GitHub"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M12 .7a11.5 11.5 0 0 0-3.64 22.41c.58.11.79-.25.79-.56v-2.24c-3.22.7-3.9-1.37-3.9-1.37-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.78 1.2 1.78 1.2 1.04 1.77 2.72 1.26 3.38.96.1-.75.4-1.26.73-1.55-2.57-.29-5.27-1.28-5.27-5.68 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.16 1.18a10.96 10.96 0 0 1 5.76 0c2.19-1.49 3.16-1.18 3.16-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.41-2.71 5.38-5.29 5.67.42.36.79 1.07.79 2.16v3.2c0 .31.21.68.8.56A11.5 11.5 0 0 0 12 .7Z"
            />
          </svg>
          <span>github.com/smitzo</span>
        </a>
      </footer>
    </div>
  );
}
