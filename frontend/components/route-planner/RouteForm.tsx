"use client";

import { FormEvent, useState } from "react";

interface RouteFormProps {
  isLoading: boolean;
  loadingSeconds: number;
  onSubmit: (start: string, finish: string) => Promise<void>;
}

const routePresets = [
  ["Los Angeles, CA", "New York, NY"],
  ["Austin, TX", "Denver, CO"],
  ["Seattle, WA", "Miami, FL"],
] as const;

export function RouteForm({
  isLoading,
  loadingSeconds,
  onSubmit,
}: RouteFormProps) {
  const [start, setStart] = useState("Los Angeles, CA");
  const [finish, setFinish] = useState("New York, NY");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onSubmit(start.trim(), finish.trim());
  }

  function swapLocations() {
    setStart(finish);
    setFinish(start);
  }

  return (
    <form className="route-form" onSubmit={handleSubmit}>
      <div className="location-fields">
        <label className="field">
          <span>Starting point</span>
          <span className="input-wrap">
            <i className="location-dot start-dot" aria-hidden="true" />
            <input
              name="start"
              value={start}
              onChange={(event) => setStart(event.target.value)}
              placeholder="City, state or address"
              maxLength={300}
              required
              disabled={isLoading}
            />
          </span>
        </label>

        <button
          className="swap-button"
          type="button"
          onClick={swapLocations}
          aria-label="Swap start and finish"
          disabled={isLoading}
        >
          ⇄
        </button>

        <label className="field">
          <span>Destination</span>
          <span className="input-wrap">
            <i className="location-dot finish-dot" aria-hidden="true" />
            <input
              name="finish"
              value={finish}
              onChange={(event) => setFinish(event.target.value)}
              placeholder="City, state or address"
              maxLength={300}
              required
              disabled={isLoading}
            />
          </span>
        </label>
      </div>

      <button className="plan-button" type="submit" disabled={isLoading}>
        {isLoading ? (
          <>
            <span className="spinner" aria-hidden="true" />
            {loadingSeconds >= 10 ? "Waking backend" : "Planning route"}
          </>
        ) : (
          <>
            Plan my route
            <span aria-hidden="true">→</span>
          </>
        )}
      </button>
      <div className="route-presets" aria-label="Example routes">
        <span>Try:</span>
        {routePresets.map(([presetStart, presetFinish]) => (
          <button
            type="button"
            key={`${presetStart}-${presetFinish}`}
            onClick={() => {
              setStart(presetStart);
              setFinish(presetFinish);
            }}
            disabled={isLoading}
          >
            {presetStart.split(",")[0]} → {presetFinish.split(",")[0]}
          </button>
        ))}
      </div>
      <p className="hosting-note">
        <span aria-hidden="true">i</span>
        The app is optimized, but it is hosted on Render&apos;s free tier.
        After inactivity, the first request may take around 10-15 seconds while
        the backend wakes up.
      </p>
    </form>
  );
}
