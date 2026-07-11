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

export async function planRoute(request: RouteRequest) {
  const response = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  const payload = (await response.json()) as RoutePlan | ApiError;
  if (!response.ok) {
    if ("error" in payload) {
      throw new RouteApiError(payload.error.message, payload.error.code);
    }
    throw new RouteApiError("Unable to plan this route.", "unknown_error");
  }

  return payload as RoutePlan;
}
