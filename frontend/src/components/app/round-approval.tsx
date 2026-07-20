"use client";

import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { scoreTone, TONE_TEXT } from "@/lib/score-tone";
import type { RoundSummary } from "@/lib/types";

const NEXT_ROUND_LABEL: Record<number, string> = {
  1: "round 2 (skill-match narrowing)",
  2: "round 3 (detailed LLM review)",
};

export function RoundApprovalCard({
  summary,
  onApprove,
}: {
  summary: RoundSummary;
  onApprove: () => Promise<void>;
}) {
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleApprove() {
    setError(null);
    setApproving(true);
    try {
      await onApprove();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to continue");
      setApproving(false);
    }
  }

  const advancing = summary.candidates.filter((c) => c.advancing).sort((a, b) => b.score - a.score);
  const notAdvancing = summary.candidates.filter((c) => !c.advancing);

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Round {summary.round} complete &mdash; {summary.label}
          </h3>
          <p className="text-xs text-muted-foreground">
            {summary.advancing_count} of {summary.candidates.length} candidates advancing. Nothing
            continues until you approve.
          </p>
        </div>
        <Button onClick={handleApprove} disabled={approving} size="sm" className="gap-1.5">
          {approving ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <ArrowRight className="size-3.5" />
          )}
          {approving ? "Starting..." : `Approve & continue to ${NEXT_ROUND_LABEL[summary.round] ?? "next round"}`}
        </Button>
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-muted-foreground">Advancing ({advancing.length})</span>
        <ul className="flex max-h-56 flex-col gap-1 overflow-y-auto">
          {advancing.map((c, i) => (
            <li
              key={c.filename}
              style={{ animationDelay: `${Math.min(i, 12) * 50}ms` }}
              className="animate-in fade-in slide-in-from-top-1 flex items-center gap-3 rounded-md border border-primary/20 bg-primary/5 px-3 py-1.5 duration-300"
            >
              <span className="truncate text-sm text-foreground">{c.filename}</span>
              <span className={cn("ml-auto shrink-0 text-sm font-semibold tabular-nums", TONE_TEXT[scoreTone(c.score)])}>
                {Math.round(c.score)}%
              </span>
            </li>
          ))}
        </ul>
      </div>

      {notAdvancing.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Not advancing ({notAdvancing.length})</span>
          <ul className="flex max-h-40 flex-col gap-1 overflow-y-auto">
            {notAdvancing.map((c) => (
              <li
                key={c.filename}
                className="flex items-center gap-3 rounded-md border border-border/60 bg-muted/20 px-3 py-1.5"
              >
                <span className="truncate text-sm text-muted-foreground">{c.filename}</span>
                <Badge variant="secondary" className="ml-auto shrink-0 bg-muted text-muted-foreground">
                  {c.eligible ? "Cut" : "Not eligible"}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
