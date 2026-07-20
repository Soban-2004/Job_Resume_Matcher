import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { scoreTone, TONE_TEXT } from "@/lib/score-tone";
import type { CandidatePhase, CandidateStatus } from "@/lib/types";

const PHASE_LABEL: Record<CandidatePhase, string> = {
  pending: "Queued",
  round1: "Prescreen…",
  round1_cut: "Cut at round 1",
  round2: "Skill-matching…",
  round2_cut: "Cut at round 2",
  round3: "Detailed review…",
  done: "Done",
};

export function CandidateProgressList({ candidates }: { candidates: CandidateStatus[] }) {
  const done = candidates.filter((c) => c.state === "done").length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-foreground">
          {done} of {candidates.length} candidates processed
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        Round 1 (free prescreen) and round 2 (skill-match) narrow the pool before round 3&apos;s
        detailed per-requirement LLM review -- each round pauses for your approval before the
        next one starts.
      </p>
      <ul className="flex flex-col gap-1">
        {candidates.map((c) => {
          const tone = c.score != null ? scoreTone(c.score) : null;
          const running = c.state === "running";
          return (
            <li
              key={c.filename}
              className="flex items-center gap-3 rounded-md border border-border px-3 py-2"
            >
              <span
                className={cn(
                  "flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px]",
                  c.state === "done" && "border-emerald-500 bg-emerald-500 text-white",
                  running && "border-primary text-primary",
                  c.state === "pending" && "border-border text-transparent"
                )}
              >
                {c.state === "done" && <Check className="size-3" />}
                {running && <Loader2 className="size-3 animate-spin" />}
              </span>
              <span className="truncate text-sm text-foreground">{c.filename}</span>
              <span className="shrink-0 text-xs text-muted-foreground/80">{PHASE_LABEL[c.phase]}</span>
              {c.score != null && (
                <span className={cn("ml-auto shrink-0 text-sm font-semibold tabular-nums", tone && TONE_TEXT[tone])}>
                  {Math.round(c.score)}%
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
