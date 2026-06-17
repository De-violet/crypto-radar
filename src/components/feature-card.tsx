import * as React from "react";
import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface FeatureCardProps extends React.HTMLAttributes<HTMLDivElement> {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function FeatureCard({
  icon: Icon,
  title,
  description,
  className,
  ...props
}: FeatureCardProps) {
  return (
    <Card
      className={cn(
        "group relative overflow-hidden border-border/60 transition-all hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5",
        className,
      )}
      {...props}
    >
      <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-accent/20 blur-2xl transition-opacity group-hover:opacity-80" />
      <CardContent className="p-6">
        <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-inset ring-primary/20">
          <Icon className="h-5 w-5" />
        </div>
        <h3 className="mb-1.5 text-lg font-semibold tracking-tight">{title}</h3>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      </CardContent>
    </Card>
  );
}
