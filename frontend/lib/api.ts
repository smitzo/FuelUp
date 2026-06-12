import type { ApiError, RoutePlan } from "@/lib/types";

export async function planRoute(start: string, finish: string) {
  const response = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start, finish }),
  });

  const payload = (await response.json()) as RoutePlan | ApiError;
  if (!response.ok) {
    const message =
      "error" in payload ? payload.error.message : "Unable to plan this route.";
    throw new Error(message);
  }

  return payload as RoutePlan;
}

