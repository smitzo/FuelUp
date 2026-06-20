import type { ApiError, RoutePlan } from "@/lib/types";

export class RouteApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
    this.name = "RouteApiError";
  }
}

export async function planRoute(start: string, finish: string) {
  const response = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start, finish }),
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
