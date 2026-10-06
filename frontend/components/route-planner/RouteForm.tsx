"use client";

import { FormEvent, useState } from "react";
import type {
  FuelType,
  PriceQualityPolicy,
  RouteRequest,
  RouteStrategy,
} from "@/lib/types";

interface RouteFormProps {
  isLoading: boolean;
  loadingSeconds: number;
  onSubmit: (request: RouteRequest) => Promise<void>;
}

const routePresets = [
  ["Ahmedabad, Gujarat", "Vadodara, Gujarat"],
  ["Mumbai, Maharashtra", "Pune, Maharashtra"],
  ["Delhi", "Jaipur, Rajasthan"],
] as const;

export function RouteForm({
  isLoading,
  loadingSeconds,
  onSubmit,
}: RouteFormProps) {
  const [start, setStart] = useState("Ahmedabad, Gujarat");
  const [finish, setFinish] = useState("Vadodara, Gujarat");
  const [waypoint, setWaypoint] = useState("");
  const [fuelType, setFuelType] = useState<FuelType>("petrol");
  const [tankCapacity, setTankCapacity] = useState(35);
  const [efficiency, setEfficiency] = useState(18);
  const [startingFuel, setStartingFuel] = useState(8);
  const [reserveFuel, setReserveFuel] = useState(3);
  const [maximumDetour, setMaximumDetour] = useState(5);
  const [strategy, setStrategy] = useState<RouteStrategy>("balanced");
  const [priceQuality, setPriceQuality] =
    useState<PriceQualityPolicy>("best_available");

  const [formError, setFormError] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    if (![tankCapacity, efficiency, startingFuel, reserveFuel, maximumDetour].every(Number.isFinite)) {
      setFormError("Please fill in all vehicle values with valid numbers.");
      return;
    }
    if (startingFuel + reserveFuel > tankCapacity) {
      setFormError("Usable starting fuel plus reserve cannot exceed the tank capacity.");
      return;
    }
    if (reserveFuel >= tankCapacity) {
      setFormError("Keep the reserve below the tank capacity so there is fuel to drive with.");
      return;
    }
    if (!waypoint.trim() && start.trim().toLowerCase() === finish.trim().toLowerCase()) {
      setFormError("Choose different starting and destination locations, or add a via point.");
      return;
    }
    void onSubmit({
      start: start.trim(),
      finish: finish.trim(),
      waypoints: waypoint.trim() ? [waypoint.trim()] : [],
      vehicle: {
        fuel_type: fuelType,
        tank_capacity: tankCapacity,
        efficiency,
        starting_fuel: startingFuel,
        reserve_fuel: reserveFuel,
      },
      maximum_detour: maximumDetour,
      strategy,
      price_quality: priceQuality,
      allow_stale_prices: false,
    });
  }

  function swapLocations() {
    setStart(finish);
    setFinish(start);
  }

  return (
    <form className="route-form" onSubmit={handleSubmit}
      onInvalidCapture={(event) => {
        const details = (event.target as HTMLElement).closest("details");
        if (details) details.open = true;
      }}>
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

      <details className="form-details">
        <summary>Vehicle &amp; fuel <span>{fuelType} · {efficiency || "—"} km/L · {startingFuel || 0} L usable</span></summary>
      <fieldset className="vehicle-panel" disabled={isLoading}>
        <legend>Your vehicle</legend>
        <div className="vehicle-fields">
          <label className="compact-field">
            <span>Fuel</span>
            <select
              value={fuelType}
              onChange={(event) => setFuelType(event.target.value as FuelType)}
            >
              <option value="petrol">Petrol</option>
              <option value="diesel">Diesel</option>
            </select>
          </label>
          <NumberField
            label="Tank (L)"
            value={tankCapacity}
            min={1}
            max={300}
            onChange={setTankCapacity}
          />
          <NumberField
            label="Mileage (km/L)"
            value={efficiency}
            min={1}
            max={100}
            step={0.1}
            onChange={setEfficiency}
          />
          <NumberField
            label="Starting fuel (L)"
            value={startingFuel}
            min={0}
            max={300}
            step={0.1}
            onChange={setStartingFuel}
          />
          <NumberField
            label="Reserve (L)"
            value={reserveFuel}
            min={0}
            max={100}
            step={0.1}
            onChange={setReserveFuel}
          />
          <NumberField
            label="Max detour (km)"
            value={maximumDetour}
            min={0.5}
            max={50}
            step={0.5}
            onChange={setMaximumDetour}
          />
        </div>
      </fieldset>
      <p className="field-help">Usable starting fuel excludes the reserve you want to keep aside.</p>
      </details>

      <details className="form-details">
        <summary>Trip options <span>Via point, route goal &amp; price quality</span></summary>
      <label className="field waypoint-field">
        <span>Via (optional)</span>
        <span className="input-wrap">
          <i className="location-dot waypoint-dot" aria-hidden="true" />
          <input
            name="waypoint"
            value={waypoint}
            onChange={(event) => setWaypoint(event.target.value)}
            placeholder="One waypoint, for example Anand, Gujarat"
            maxLength={300}
            disabled={isLoading}
          />
        </span>
      </label>

      <div className="preference-fields">
        <label className="compact-field">
          <span>Route goal</span>
          <select
            value={strategy}
            onChange={(event) =>
              setStrategy(event.target.value as RouteStrategy)
            }
            disabled={isLoading}
          >
            <option value="balanced">Balanced</option>
            <option value="cheapest_estimated">Lowest estimated cost</option>
            <option value="fastest">Fastest</option>
          </select>
        </label>
        <label className="compact-field">
          <span>Price quality</span>
          <select
            value={priceQuality}
            onChange={(event) =>
              setPriceQuality(event.target.value as PriceQualityPolicy)
            }
            disabled={isLoading}
          >
            <option value="best_available">Best available</option>
            <option value="station_reported_only">Station reports only</option>
          </select>
        </label>
      </div>

      </details>

      {formError ? <p className="form-error" role="alert">{formError}</p> : null}
      <button className="plan-button" type="submit" disabled={isLoading}>
        {isLoading ? (
          <>
            <span className="spinner" aria-hidden="true" />
            {loadingSeconds >= 10 ? "Still planning…" : "Planning route…"}
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
        India pilot. Prices may be city references or station reports.
        Check the source and update time before you fill up.
      </p>
    </form>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="compact-field">
      <span>{label}</span>
      <input
        type="number"
        value={Number.isFinite(value) ? value : ""}
        min={min}
        max={max}
        step={step}
        required
        onChange={(event) => onChange(event.target.valueAsNumber)}
      />
    </label>
  );
}
