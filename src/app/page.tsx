import Link from "next/link";
import {
  ArrowRight,
  Bell,
  History,
  Layers,
  Radar,
  Sparkles,
} from "lucide-react";

import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { FeatureCard } from "@/components/feature-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const features = [
  {
    icon: Layers,
    title: "Multi-Strategy",
    description:
      "Three battle-tested strategies — trend-following, mean-reversion, and breakout — run in parallel so you never rely on a single edge.",
  },
  {
    icon: Bell,
    title: "Real-time Alerts",
    description:
      "Get notified the moment a high-conviction setup forms. Delivered to Discord, email, and the dashboard in under a second.",
  },
  {
    icon: History,
    title: "Backtest-validated",
    description:
      "Every signal is scored against years of historical data with strict 1:2 risk-reward before it ever reaches you.",
  },
];

const stats = [
  { label: "coins scanned", value: "120+" },
  { label: "strategies", value: "3" },
  { label: "R:R ratio", value: "1:2" },
  { label: "always-on", value: "24/7" },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />

      <main className="flex-1">
        {/* ───────────────────────── Hero ───────────────────────── */}
        <section className="relative overflow-hidden">
          {/* Ambient violet glow */}
          <div className="pointer-events-none absolute inset-0 -z-10">
            <div className="absolute left-1/2 top-0 h-[400px] w-[600px] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]" />
            <div className="absolute right-0 top-40 h-[300px] w-[300px] rounded-full bg-accent/30 blur-[100px]" />
          </div>

          <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8 lg:py-32">
            <div className="mx-auto max-w-3xl text-center">
              <Badge
                variant="outline"
                className="mb-6 border-primary/30 bg-primary/5 text-primary"
              >
                <Sparkles className="mr-1.5 h-3 w-3" />
                Phase 0 — Skeleton preview
              </Badge>

              <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
                Catch high-conviction crypto entries,{" "}
                <span className="text-gradient-violet">automatically</span>
              </h1>

              <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg text-muted-foreground sm:text-xl">
                Crypto Radar scans 120+ coins across multiple validated
                strategies and surfaces only the setups that meet strict
                risk-reward criteria — so you act with conviction, not FOMO.
              </p>

              <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Button asChild size="lg" className="w-full sm:w-auto">
                  <Link href="/login">
                    Get Started Free
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto"
                >
                  <Link href="/dashboard">
                    <Radar className="mr-1 h-4 w-4" />
                    View Dashboard
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* ─────────────────────── Stats row ─────────────────────── */}
        <section className="border-y border-border/60 bg-muted/30">
          <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
            <dl className="grid grid-cols-2 gap-6 sm:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="text-center">
                  <dd className="font-mono text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                    {stat.value}
                  </dd>
                  <dt className="mt-1 text-sm text-muted-foreground">
                    {stat.label}
                  </dt>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* ─────────────────────── Features ─────────────────────── */}
        <section id="features" className="scroll-mt-20">
          <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
            <div className="mx-auto mb-14 max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Everything you need to trade with conviction
              </h2>
              <p className="mt-4 text-muted-foreground">
                Built by traders, for traders. No noise — just signals that
                pass the bar.
              </p>
            </div>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature) => (
                <FeatureCard
                  key={feature.title}
                  icon={feature.icon}
                  title={feature.title}
                  description={feature.description}
                />
              ))}
            </div>
          </div>
        </section>

        {/* ─────────────────────── Strategies teaser ─────────────────────── */}
        <section
          id="strategies"
          className="scroll-mt-20 border-t border-border/60 bg-muted/30"
        >
          <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
            <div className="flex flex-col items-start justify-between gap-6 lg:flex-row lg:items-center">
              <div className="max-w-xl">
                <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                  Ready to see the radar in action?
                </h2>
                <p className="mt-4 text-muted-foreground">
                  The dashboard is a live skeleton right now. Real signals,
                  backtests, and strategy breakdowns land in Phase 1.
                </p>
              </div>
              <Button asChild size="lg">
                <Link href="/dashboard">
                  Open Dashboard
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
