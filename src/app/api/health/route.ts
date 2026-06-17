import { NextResponse } from "next/server";

import { apiUrl, type HealthResponse } from "@/lib/api-client";

/**
 * GET /api/health
 *
 * Probes the Python FastAPI backend's `/health` endpoint from the server side
 * (avoids CORS / exposing the backend URL to the browser). Returns 200 with
 * the backend payload when reachable, or 503 with `{ status: "unreachable" }`
 * on any failure.
 *
 * Backend base URL resolution order:
 *   1. process.env.API_BASE_URL        (server-only, optional)
 *   2. process.env.NEXT_PUBLIC_API_BASE_URL
 *   3. "http://localhost:8000"          (fallback for local dev)
 */
export async function GET() {
  const baseUrl =
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000";

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(apiUrl("/health", baseUrl), {
      method: "GET",
      signal: controller.signal,
      headers: { Accept: "application/json" },
      // Always fetch fresh health status
      cache: "no-store",
    });

    clearTimeout(timeout);

    if (!response.ok) {
      return NextResponse.json(
        {
          status: "unhealthy",
          upstream_status: response.status,
          message: `Backend responded with ${response.status}`,
        },
        { status: 502 },
      );
    }

    const data = (await response.json()) as HealthResponse;
    return NextResponse.json(
      {
        status: "ok",
        upstream: data,
        timestamp: new Date().toISOString(),
      },
      { status: 200 },
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        status: "unreachable",
        message,
        baseUrl,
      },
      { status: 503 },
    );
  }
}
