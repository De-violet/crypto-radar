import { Activity, Crosshair, Percent, TrendingUp } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

const statCards = [
  { title: "Total Signals", icon: Activity, accent: "text-primary" },
  { title: "Win Rate", icon: Percent, accent: "text-emerald-500" },
  { title: "Active Strategies", icon: Crosshair, accent: "text-amber-500" },
  { title: "Avg R:R", icon: TrendingUp, accent: "text-sky-500" },
];

export default function DashboardOverviewPage() {
  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
        <p className="text-sm text-muted-foreground">
          A snapshot of your signal performance. Data wires up in Phase 1.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <Card key={stat.title} className="border-border/60">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.accent}`} />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-24" />
              <Skeleton className="mt-2 h-3 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent signals table placeholder */}
      <Card className="border-border/60">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div className="space-y-1">
            <CardTitle className="text-lg">Recent Signals</CardTitle>
            <p className="text-sm text-muted-foreground">
              Latest entries across all strategies.
            </p>
          </div>
          <Badge variant="outline" className="text-xs">
            Loading…
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          {/* Table header */}
          <div className="hidden grid-cols-12 gap-4 border-b border-border/60 px-6 py-3 text-xs font-medium uppercase tracking-wide text-muted-foreground sm:grid">
            <div className="col-span-3">Pair</div>
            <div className="col-span-2">Strategy</div>
            <div className="col-span-2">Side</div>
            <div className="col-span-2">Entry</div>
            <div className="col-span-3">Status</div>
          </div>

          {/* Skeleton rows */}
          <div className="divide-y divide-border/60">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="grid grid-cols-2 gap-4 px-6 py-4 sm:grid-cols-12"
              >
                <div className="col-span-2 flex items-center gap-2 sm:col-span-3">
                  <Skeleton className="h-6 w-6 rounded-full" />
                  <Skeleton className="h-4 w-20" />
                </div>
                <div className="hidden items-center sm:col-span-2 sm:flex">
                  <Skeleton className="h-4 w-16" />
                </div>
                <div className="hidden items-center sm:col-span-2 sm:flex">
                  <Skeleton className="h-5 w-12 rounded-md" />
                </div>
                <div className="hidden items-center font-mono sm:col-span-2 sm:flex">
                  <Skeleton className="h-4 w-20" />
                </div>
                <div className="hidden items-center sm:col-span-3 sm:flex">
                  <Skeleton className="h-5 w-20 rounded-md" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
