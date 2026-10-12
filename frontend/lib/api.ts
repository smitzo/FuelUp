import type { ApiError, RoutePlan, RouteRequest } from "@/lib/types";

export class RouteApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
    this.name = "RouteApiError";
  }
}

export async function planRoute(request: RouteRequest, signal?: AbortSignal) {
  const response = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  let payload: RoutePlan | ApiError;
  try { payload = await response.json() as RoutePlan | ApiError; }
  catch { throw new RouteApiError("The route service returned an unreadable response. Please try again.", "backend_unavailable"); }
  if (!payload || typeof payload !== "object") {
    throw new RouteApiError("The route service returned an invalid response.", "backend_unavailable");
  }
  if (!response.ok) {
    if ("error" in payload && payload.error && typeof payload.error.message === "string") {
      throw new RouteApiError(payload.error.message, payload.error.code);
    }
    throw new RouteApiError("Unable to plan this route.", "unknown_error");
  }

  if (!("api_version" in payload) || payload.api_version !== "v2" || !("route" in payload) || !("fuel_plan" in payload)) {
    throw new RouteApiError("The route service returned an incompatible plan.", "backend_unavailable");
  }
  return payload as RoutePlan;
}
