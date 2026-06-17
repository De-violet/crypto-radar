import Link from "next/link";
import { Github } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-border/60 bg-background">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:px-6 lg:px-8">
        <p>
          Built with{" "}
          <span className="font-medium text-foreground">Next.js</span> +{" "}
          <span className="font-medium text-foreground">Supabase</span>
        </p>
        <div className="flex items-center gap-4">
          <span className="text-xs">© {new Date().getFullYear()} Crypto Radar</span>
          <Link
            href="https://github.com/De-violet/crypto-radar"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 transition-colors hover:text-foreground"
          >
            <Github className="h-4 w-4" />
            <span>GitHub</span>
          </Link>
        </div>
      </div>
    </footer>
  );
}
