import { RouteApiError } from "@/lib/api";

export function plannerError(error: unknown): { title: string; message: string } {
  if (error instanceof RouteApiError) {
    if (error.code === "insufficient_price_data" || error.code === "station_catalogue_unavailable") {
      return { title: "Price coverage is not ready", message: "We don’t have enough current prices for this trip. Try another route or return after the next update." };
    }
    if (error.code === "unsupported_country") {
      return { title: "India routes only", message: "Choose starting, destination, and via locations within India." };
    }
    if (error.code === "location_not_found") {
      return { title: "We couldn’t find that place", message: "Add the state or a nearby town and try again." };
    }
    if (["provider_budget_exceeded", "rate_limited", "rate_limit_exceeded"].includes(error.code)) {
      return { title: "Please try again later", message: "The request allowance has been reached. Your vehicle details are still here." };
    }
    if (error.code === "external_service_error" || error.code === "backend_unavailable") {
      return { title: "The route service is unavailable", message: "Please try again shortly. We’ll keep your trip details here." };
    }
    if (error.code === "fuel_plan_not_found") {
      return { title: "No reachable fuel plan", message: "Check your starting fuel, reserve, mileage, and maximum detour. We couldn’t find enough reachable stops for this vehicle." };
    }
    return { title: "Unable to plan this trip", message: error.message };
  }
  return { title: "Connection interrupted", message: "Check your connection and try again. Your trip details are still here." };
}
