"use client";

import { useState } from "react";

interface RouteLoadingProps {
  loadingSeconds: number;
  source: string;
  destination: string;
}

const routeFacts = [
  "A 500-mile range at 10 MPG implies a 50-gallon usable tank.",
  "FuelUp asks OSRM for route alternatives in one routing request.",
  "The fuel optimizer buys only enough to reach a cheaper reachable station.",
  "Repeated route requests are cached, so the same trip should return faster.",
  "Station candidates are projected onto the route instead of matched to map pins.",
];

export function RouteLoading({
  loadingSeconds,
  source,
  destination,
}: RouteLoadingProps) {
  const [factOffset, setFactOffset] = useState(0);
  const factIndex =
    (Math.floor(loadingSeconds / 4) + factOffset) % routeFacts.length;
  const isWaking = loadingSeconds >= 5;

  return (
    <section className="route-loading" aria-live="polite" aria-busy="true">
      <div className="loading-scene" aria-hidden="true">
        <div className="loading-sky">
          <span className="loading-cloud cloud-one" />
          <span className="loading-cloud cloud-two" />
        </div>
        <div className="loading-landmark landmark-start">
          <span />
          <b title={source}>{source}</b>
        </div>
        <div className="loading-landmark landmark-finish">
          <span />
          <b title={destination}>{destination}</b>
        </div>
        <div className="loading-road">
          <span className="road-lines" />
          <span className="loading-truck">
            <i className="truck-tank" />
            <i className="truck-cab" />
            <i className="truck-window" />
            <i className="truck-wheel wheel-front" />
            <i className="truck-wheel wheel-middle" />
            <i className="truck-wheel wheel-back" />
          </span>
        </div>
      </div>

      <div className="loading-copy">
        <p className="eyebrow">
          {isWaking ? "Starting the route engine" : "Calculating your trip"}
        </p>
        <h2>
          {isWaking
            ? "The free backend is waking up."
            : "Finding the smartest fuel stops."}
        </h2>
        <p className="loading-status">
          {isWaking
            ? "FuelUp is optimized, but Render's free tier sleeps after inactivity. The first request can take around 10-15 seconds."
            : "Comparing route alternatives, station prices, and fuel purchases."}
        </p>

        <div className="loading-progress" aria-hidden="true">
          <span />
        </div>

        <div className="fact-card">
          <div>
            <span className="fact-label">Road-trip fact</span>
            <p>{routeFacts[factIndex]}</p>
          </div>
          <button
            type="button"
            onClick={() => setFactOffset((offset) => offset + 1)}
          >
            Another fact
          </button>
        </div>

        <p className="loading-timer">{loadingSeconds}s elapsed</p>
      </div>
    </section>
  );
}
