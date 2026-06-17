"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ThemeProviderProps } from "next-themes";

/**
 * Wraps the app with next-themes. Default theme is `dark` (violet luxury looks
 * best on dark), respects user system preference, and stores choice in a cookie
 * so it persists across reloads and SSR.
 */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
