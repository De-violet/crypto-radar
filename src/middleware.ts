import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware — protect `/dashboard/*` routes.
 *
 * Phase 0 (this phase): a lightweight cookie-existence check for `sb-session`.
 * This is a placeholder — real Supabase session validation (JWT verification
 * via @supabase/ssr) is wired up in Phase 1.
 *
 * Any request without an `sb-session` cookie is redirected to `/login`,
 * preserving the original path as a `?redirect=` query param.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow requests for Next.js internals and static assets.
  const sessionCookie = request.cookies.get("sb-session");

  if (!sessionCookie) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Run on all dashboard routes (including nested ones).
  matcher: ["/dashboard/:path*"],
};
