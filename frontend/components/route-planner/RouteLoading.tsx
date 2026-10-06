"use client";

import { useState } from "react";

interface RouteLoadingProps {
  loadingSeconds: number;
  source: string;
  destination: string;
}

const routeFacts = [
  "FuelUp calculates range from your tank, reserve, and km/l efficiency.",
  "A city reference price can differ from the amount charged at an individual pump.",
  "Keep a fuel reserve for unexpected diversions and queues.",
  "Repeated route requests are cached, so the same trip should return faster.",
  "Check the price and fuel grade at the pump before filling up.",
];

export function RouteLoading({
  loadingSeconds,
  source,
  destination,
}: RouteLoadingProps) {
  const [factOffset, setFactOffset] = useState(0);
  const factIndex =
    (Math.floor(loadingSeconds / 4) + factOffset) % routeFacts.length;
  const isTakingLonger = loadingSeconds >= 10;

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
          {isTakingLonger ? "Taking a little longer" : "Calculating your trip"}
        </p>
        <h2>
          {isTakingLonger
            ? "Your trip is still being planned."
            : "Finding fuel stops along the way."}
        </h2>
        <p className="loading-status">
          {isTakingLonger
            ? "The route service may take a moment on the first request. You can cancel and try again."
            : "Comparing route alternatives, station prices, and fuel purchases."}
        </p>

        <div className="loading-progress" aria-hidden="true">
          <span />
        </div>

        <div className="fact-card">
          <div>
            <span className="fact-label">Along the way</span>
            <p>{routeFacts[factIndex]}</p>
          </div>
          <button
            type="button"
            onClick={() => setFactOffset((offset) => offset + 1)}
          >
            Another tip
          </button>
        </div>

        <p className="loading-timer">{loadingSeconds}s elapsed</p>
      </div>
    </section>
  );
}
