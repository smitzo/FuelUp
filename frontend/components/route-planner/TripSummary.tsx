import { formatCurrency, formatDuration, formatNumber } from "@/lib/format";
import type { RoutePlan } from "@/lib/types";

interface TripSummaryProps {
  plan: RoutePlan;
}

export function TripSummary({ plan }: TripSummaryProps) {
  const currency = plan.market.currency_code;
  const metrics = [
    {
      label: "Route distance",
      value: `${formatNumber(plan.route.distance)} ${plan.market.distance_unit}`,
      detail: formatDuration(plan.route.duration_hours),
    },
    {
      label: "Fuel stops",
      value: String(plan.fuel_plan.stops.length),
      detail: `${formatNumber(plan.vehicle.maximum_range)} ${plan.market.distance_unit} usable range`,
    },
    {
      label: "Fuel used on this route",
      value: `${formatNumber(plan.fuel_plan.total_consumed_volume)} ${plan.market.volume_unit}`,
      detail: `${formatNumber(plan.vehicle.efficiency)} ${plan.market.efficiency_unit}`,
    },
    {
      label: "Estimated top-up spend",
      value: formatCurrency(plan.fuel_plan.purchase_cost, currency),
      detail: `${formatNumber(plan.fuel_plan.purchased_volume)} ${plan.market.volume_unit} to buy · starting fuel excluded`,
      emphasis: true,
    },
  ];

  return (
    <div className="summary-section">
      <div className="route-heading">
        <div>
          <p className="eyebrow">
            {plan.market.country_name} route plan
          </p>
          <h2>
            {plan.start.query} <span aria-hidden="true">→</span>{" "}
            {plan.finish.query}
          </h2>
        </div>
        <span className="route-badge">
          {plan.metadata.strategy.replaceAll("_", " ")} · best of {" "}
          {plan.metadata.route_alternatives_evaluated} routes
        </span>
      </div>

      <div className="metric-grid">
        {metrics.map((metric) => (
          <article
            className={`metric-card${metric.emphasis ? " metric-emphasis" : ""}`}
            key={metric.label}
          >
            <p>{metric.label}</p>
            <strong>{metric.value}</strong>
            <span>{metric.detail}</span>
          </article>
        ))}
      </div>
      <p className="summary-note">Driving time and fuel spend are estimates. You should arrive with {formatNumber(plan.fuel_plan.arrival_fuel)} {plan.market.volume_unit} of usable fuel, plus your protected reserve.</p>
    </div>
  );
}
