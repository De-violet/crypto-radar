/**
 * Supabase client placeholder.
 *
 * Real Supabase Auth integration is deferred to Phase 1. Calling any of these
 * helpers in Phase 0 throws so it is obvious the feature is not wired yet.
 *
 * When Phase 1 lands, replace this file with:
 *   import { createBrowserClient } from "@supabase/ssr";
 *   export const supabase = createBrowserClient(
 *     process.env.NEXT_PUBLIC_SUPABASE_URL!,
 *     process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
 *   );
 * (and add a server-side client using @supabase/ssr cookies helpers).
 */

const NOT_IMPLEMENTED = "Supabase Auth is not implemented in Phase 0.";

export function getSupabaseClient(): never {
  throw new Error(NOT_IMPLEMENTED);
}

export async function signInWithGoogle(): Promise<never> {
  throw new Error(NOT_IMPLEMENTED);
}

export async function signInWithGithub(): Promise<never> {
  throw new Error(NOT_IMPLEMENTED);
}

export async function signInWithEmail(): Promise<never> {
  throw new Error(NOT_IMPLEMENTED);
}

export async function signOut(): Promise<never> {
  throw new Error(NOT_IMPLEMENTED);
}

export async function getSession(): Promise<never> {
  throw new Error(NOT_IMPLEMENTED);
}
