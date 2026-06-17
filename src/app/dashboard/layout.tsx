import Link from "next/link";
import {
  LayoutDashboard,
  ListChecks,
  SlidersHorizontal,
  History,
  Settings,
  Radar,
  LogOut,
} from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/signals", label: "Signals", icon: ListChecks },
  { href: "/dashboard/strategies", label: "Strategies", icon: SlidersHorizontal },
  { href: "/dashboard/backtest", label: "Backtest", icon: History },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Top bar */}
      <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-border/60 bg-background/80 px-4 backdrop-blur-md sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-primary-foreground shadow-md shadow-primary/20">
            <Radar className="h-5 w-5" />
          </span>
          <span className="text-lg font-semibold tracking-tight">
            Crypto Radar
          </span>
          <Badge variant="outline" className="ml-1 hidden sm:inline-flex">
            Phase 0
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden text-sm text-muted-foreground sm:inline">
            Welcome back
          </span>
          <ThemeToggle />
          <Button asChild variant="ghost" size="sm">
            <Link href="/login">
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Logout</span>
            </Link>
          </Button>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-4 sm:p-6 lg:flex-row lg:gap-8 lg:p-8">
        {/* Sidebar */}
        <aside className="lg:w-60 lg:shrink-0">
          <nav className="flex gap-1 overflow-x-auto rounded-xl border border-border/60 bg-card p-2 lg:sticky lg:top-24 lg:flex-col scrollbar-thin">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent/40 hover:text-foreground",
                  "lg:shrink",
                )}
              >
                <item.icon className="h-4 w-4" />
                <span className="whitespace-nowrap">{item.label}</span>
              </Link>
            ))}
          </nav>
        </aside>

        {/* Main content */}
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
