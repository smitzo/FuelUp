import { NextResponse } from "next/server";

export const maxDuration = 300;

const backendUrl =
  process.env.DJANGO_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";
const transientStatuses = new Set([502, 503, 504]);
const coldStartDeadlineMs = 90_000;

export async function POST(request: Request) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "invalid_request",
          message: "Request body must be valid JSON.",
        },
      },
      { status: 400 },
    );
  }

  const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
  const clientIp =
    request.headers.get("x-forwarded-for")?.split(",", 1)[0]?.trim() ??
    request.headers.get("x-real-ip") ??
    "unknown";
  const deadline = Date.now() + coldStartDeadlineMs;

  try {
    let response = await requestRoute(body, clientIp, requestId, 15_000);
    if (!transientStatuses.has(response.status)) {
      return proxyResponse(response);
    }

    await waitForBackend(deadline, requestId);
    response = await requestRoute(
      body,
      clientIp,
      requestId,
      Math.max(30_000, deadline - Date.now()),
    );
    return proxyResponse(response);
  } catch {
    try {
      await waitForBackend(deadline, requestId);
      const response = await requestRoute(
        body,
        clientIp,
        requestId,
        Math.max(30_000, deadline - Date.now()),
      );
      return proxyResponse(response);
    } catch {
      return NextResponse.json(
        {
          error: {
            code: "backend_unavailable",
            message:
              "The route service is temporarily unavailable. Please retry shortly.",
          },
        },
        {
          status: 503,
          headers: {
            "Retry-After": "5",
            "X-Request-ID": requestId,
          },
        },
      );
    }
  }
}

async function requestRoute(
  body: unknown,
  clientIp: string,
  requestId: string,
  timeoutMs: number,
) {
  return fetch(`${backendUrl}/api/route/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Forwarded-For": clientIp,
      "X-Request-ID": requestId,
    },
    body: JSON.stringify(body),
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
}

async function waitForBackend(deadline: number, requestId: string) {
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${backendUrl}/api/health/ready/`, {
        headers: { "X-Request-ID": requestId },
        cache: "no-store",
        signal: AbortSignal.timeout(5_000),
      });
      if (response.ok) {
        return;
      }
    } catch {
      // The backend may be restarting or briefly unavailable during deployment.
    }
    await sleep(2_000);
  }
  throw new Error("Backend did not become ready before the deadline.");
}

async function proxyResponse(response: Response) {
  const payload = await response.json();
  const nextResponse = NextResponse.json(payload, { status: response.status });
  for (const header of [
    "retry-after",
    "x-request-id",
    "x-fuelup-cache",
    "x-fuelup-cache-ttl",
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
}

function sleep(milliseconds: number) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
