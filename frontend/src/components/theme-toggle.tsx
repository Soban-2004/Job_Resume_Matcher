"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // This is one of the few legitimate exceptions to "don't setState in an
  // effect": next-themes resolves the persisted/system theme via a
  // synchronous script before React hydrates, so `resolvedTheme` is already
  // defined on the client's very first render -- it is NOT reliably
  // `undefined` pre-mount the way the library's own docs suggest. Checking
  // resolvedTheme alone caused a real hydration mismatch (server always
  // renders the placeholder, client immediately rendered the real button).
  // An explicit mounted flag guarantees the server and client's first paint
  // are identical; only after that effect fires does it swap to the real icon.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="size-8" aria-hidden />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="ghost"
      size="icon"
      className="rounded-full"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}
