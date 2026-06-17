import Link from "next/link";
import { Github, Mail, Radar } from "lucide-react";

import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />

      <main className="flex flex-1 items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <span className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-primary-foreground shadow-lg shadow-primary/30">
              <Radar className="h-6 w-6" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">
              Sign in to Crypto Radar
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Welcome back. Pick up where you left off.
            </p>
          </div>

          <Card className="border-border/60 shadow-xl shadow-primary/5">
            <CardHeader className="space-y-1">
              <CardTitle className="text-xl">Sign in</CardTitle>
              <CardDescription>
                Authentication is wired up in Phase 1 — these buttons are
                placeholders for now.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-3">
              {/* Google */}
              <Button
                variant="outline"
                className="w-full"
                disabled
                title="Supabase OAuth lands in Phase 1"
              >
                <GoogleIcon className="h-4 w-4" />
                Continue with Google
              </Button>

              {/* GitHub */}
              <Button
                variant="outline"
                className="w-full"
                disabled
                title="Supabase OAuth lands in Phase 1"
              >
                <Github className="h-4 w-4" />
                Continue with GitHub
              </Button>

              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-border" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">
                    or
                  </span>
                </div>
              </div>

              {/* Email */}
              <form className="space-y-3" action="/dashboard" method="get">
                <Input
                  type="email"
                  name="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  disabled
                  aria-label="Email address"
                />
                <Button
                  type="submit"
                  className="w-full"
                  disabled
                  title="Email magic-link auth lands in Phase 1"
                >
                  <Mail className="h-4 w-4" />
                  Continue with Email
                </Button>
              </form>
            </CardContent>

            <CardFooter className="flex flex-col gap-3">
              <p className="text-center text-sm text-muted-foreground">
                Don&apos;t have an account?{" "}
                <Link
                  href="/login"
                  className="font-medium text-primary underline-offset-4 hover:underline"
                >
                  Sign up
                </Link>
              </p>
              <Badge variant="outline" className="mx-auto text-xs">
                Phase 0 — placeholders only
              </Badge>
            </CardFooter>
          </Card>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}

/** Minimal inline Google "G" mark (keeps bundle small — no icon dep needed). */
function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="currentColor"
    >
      <path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z" />
    </svg>
  );
}
