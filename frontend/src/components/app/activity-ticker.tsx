"use client";

import { Loader2 } from "lucide-react";

export function ActivityTicker({ text }: { text: string | null }) {
  if (!text) return null;

  return (
    <div className="flex items-center gap-2 rounded-md bg-primary/5 px-3 py-2 text-sm text-foreground/80">
      <Loader2 className="size-3.5 shrink-0 animate-spin text-primary" />
      <span key={text} className="animate-in fade-in slide-in-from-left-1 duration-300">
        {text}
      </span>
    </div>
  );
}
