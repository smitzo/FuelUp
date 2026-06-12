import { formatCurrency, formatDuration, formatNumber } from "@/lib/format";
import type { RoutePlan } from "@/lib/types";

interface TripSummaryProps {
  plan: RoutePlan;
}

export function TripSummary({ plan }: TripSummaryProps) {
  const metrics = [
    {
      label: "Route distance",
      value: `${formatNumber(plan.route.distance_miles)} mi`,
      detail: formatDuration(plan.route.duration_hours),
    },
    {
      label: "Fuel stops",
      value: String(plan.fuel_plan.stops.length),
      detail: `${plan.vehicle.maximum_range_miles}-mile max range`,
    },
    {
      label: "Fuel needed",
      value: `${formatNumber(plan.fuel_plan.total_gallons)} gal`,
      detail: `${plan.vehicle.fuel_economy_mpg} miles per gallon`,
    },
    {
      label: "Estimated fuel cost",
      value: formatCurrency(plan.fuel_plan.total_cost_usd),
      detail: "Based on listed prices",
      emphasis: true,
    },
  ];

  return (
    <div className="summary-section">
      <div className="route-heading">
        <div>
          <p className="eyebrow">Optimized route</p>
          <h2>
            {plan.start.query} <span aria-hidden="true">→</span>{" "}
            {plan.finish.query}
          </h2>
        </div>
        <span className="route-badge">Route ready</span>
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
    </div>
  );
}

