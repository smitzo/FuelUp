import { formatCurrency, formatNumber, formatTimestamp } from "@/lib/format";
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
          {plan.data_quality.price_coverage_percent}% price coverage
        </span>
      </div>

      <div className="initial-fuel">
        <span className="fuel-icon" aria-hidden="true">
          ◒
        </span>
        <div>
          <strong>Fuel already available</strong>
          <p>
            {formatNumber(plan.fuel_plan.starting_fuel)} {plan.market.volume_unit} usable · {" "}
            {formatNumber(plan.fuel_plan.reserve_fuel)} {plan.market.volume_unit} protected reserve
          </p>
        </div>
      </div>

      {plan.fuel_plan.stops.length === 0 ? (
        <p className="no-stops">Your starting fuel covers this route while keeping the reserve aside. No top-up is needed.</p>
      ) : null}
      <ol className="stop-list">
        {plan.fuel_plan.stops.map((stop) => (
          <li
            className={`stop-card${
              selectedStop === stop.sequence ? " stop-card-selected" : ""
            }`}
            key={`${stop.station_id}-${stop.sequence}`}
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
                    {[stop.city, stop.state].filter(Boolean).join(", ") || "Address unavailable"} · {" "}
                    {formatNumber(stop.route_distance, 0)} {plan.market.distance_unit}
                  </p>
                </div>
                <strong>{formatCurrency(stop.cost, plan.market.currency_code)}</strong>
              </div>
              <div className="stop-details">
                <span>
                  <b>{formatCurrency(stop.unit_price, plan.market.currency_code)}</b>/{plan.market.volume_unit}
                </span>
                <span>{formatNumber(stop.volume)} {plan.market.volume_unit}</span>
                <span>
                  {formatNumber(stop.fuel_on_arrival)} {plan.market.volume_unit} on arrival
                </span>
                <span>{formatNumber(stop.distance_to_route)} {plan.market.distance_unit} away</span>
                <span className={`price-label price-${stop.price.label}`}>
                  {stop.price.label} · {stop.price.geographic_precision} · {" "}
                  {stop.price.confidence} confidence
                </span>
                <span className="price-timestamp">Updated <time dateTime={stop.price.as_of}>{formatTimestamp(stop.price.as_of)}</time></span>
                <span className="price-timestamp">Valid until {formatTimestamp(stop.price.expires_at)}</span>
              </div>
            </button>
          </li>
        ))}
      </ol>
    </aside>
  );
}
