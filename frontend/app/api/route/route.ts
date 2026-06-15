import { NextResponse } from "next/server";

const backendUrl =
  process.env.DJANGO_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

export async function POST(request: Request) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: { code: "invalid_request", message: "Request body must be valid JSON." } },
      { status: 400 },
    );
  }

  try {
    const clientIp =
      request.headers.get("x-forwarded-for")?.split(",", 1)[0]?.trim() ??
      request.headers.get("x-real-ip") ??
      "unknown";
    const response = await fetch(`${backendUrl}/api/route/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Forwarded-For": clientIp,
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    const payload = await response.json();
    const nextResponse = NextResponse.json(payload, { status: response.status });
    for (const header of [
      "retry-after",
      "x-ratelimit-limit",
      "x-ratelimit-remaining",
      "x-ratelimit-reset",
    ]) {
      const value = response.headers.get(header);
      if (value) {
        nextResponse.headers.set(header, value);
      }
    }
    return nextResponse;
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "backend_unavailable",
          message: "Server seems down. The route service is unavailable.",
        },
      },
      { status: 502 },
    );
  }
}
