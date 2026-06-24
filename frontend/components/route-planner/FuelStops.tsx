import { formatCurrency, formatNumber } from "@/lib/format";
import type { RoutePlan } from "@/lib/types";

interface FuelStopsProps {
  plan: RoutePlan;
  selectedStop: number | null;
  onSelectStop: (sequence: number) => void;
}

export function FuelStops({
  plan,
  selectedStop,
  onSelectStop,
}: FuelStopsProps) {
  return (
    <aside className="stops-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Fuel plan</p>
          <h2>{plan.fuel_plan.stops.length} recommended stops</h2>
        </div>
        <span className="savings-chip">
          {plan.metadata.demo ? "Illustrative plan" : "Cost optimized"}
        </span>
      </div>

      <div className="initial-fuel">
        <span className="fuel-icon" aria-hidden="true">
          ◒
        </span>
        <div>
          <strong>Initial fuel estimate</strong>
          <p>
            {formatNumber(plan.fuel_plan.initial_fuel_estimate.gallons)} gal ·{" "}
            {formatCurrency(plan.fuel_plan.initial_fuel_estimate.cost_usd)}
          </p>
        </div>
      </div>

      <ol className="stop-list">
        {plan.fuel_plan.stops.map((stop) => (
          <li
            className={`stop-card${
              selectedStop === stop.sequence ? " stop-card-selected" : ""
            }`}
            key={`${stop.opis_id}-${stop.sequence}`}
          >
            <span className="stop-number">{stop.sequence}</span>
            <button
              className="stop-content"
              type="button"
              onClick={() => onSelectStop(stop.sequence)}
              aria-label={`Show ${stop.name} on map`}
            >
              <div className="stop-title">
                <div>
                  <h3>{stop.name}</h3>
                  <p>
                    {stop.city}, {stop.state} · Mile{" "}
                    {formatNumber(stop.route_mile, 0)}
                  </p>
                </div>
                <strong>{formatCurrency(stop.cost_usd)}</strong>
              </div>
              <div className="stop-details">
                <span>
                  <b>{formatCurrency(stop.price_per_gallon_usd)}</b>/gal
                </span>
                <span>{formatNumber(stop.gallons)} gallons</span>
                <span>
                  {formatNumber(stop.fuel_on_arrival_gallons)} gal on arrival
                </span>
                <span>{formatNumber(stop.distance_to_route_miles)} mi away</span>
              </div>
            </button>
          </li>
        ))}
      </ol>
    </aside>
  );
}
