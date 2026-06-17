/**
 * Lightweight fetch wrapper for the Python FastAPI backend.
 *
 * Phase 0: only `/health` is consumed (server-side in /api/health route).
 * Phase 1 will expand this to signals, strategies, backtests, etc.
 */

const DEFAULT_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface ApiError extends Error {
  status?: number;
  cause?: unknown;
}

/**
 * Build an absolute URL for a given API path.
 */
export function apiUrl(path: string, baseUrl: string = DEFAULT_BASE_URL): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl.replace(/\/$/, "")}${normalizedPath}`;
}

/**
 * Fetch JSON from the backend with a timeout and structured error handling.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  baseUrl?: string,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.signal ? 0 : 8000);

  try {
    const response = await fetch(apiUrl(path, baseUrl), {
      ...options,
      signal: options.signal ?? controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = new Error(
        `API request failed: ${response.status} ${response.statusText}`,
      ) as ApiError;
      error.status = response.status;
      throw error;
    }

    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Health check response shape from the Python backend `/health` endpoint.
 */
export interface HealthResponse {
  status: string;
  timestamp?: string;
  version?: string;
  [key: string]: unknown;
}
