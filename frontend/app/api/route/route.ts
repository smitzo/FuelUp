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
    const response = await fetch(`${backendUrl}/api/route/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "backend_unavailable",
          message: "The route service is unavailable. Confirm that Django is running.",
        },
      },
      { status: 502 },
    );
  }
}

