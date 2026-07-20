import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CandidateResult } from "@/lib/types";

interface Stage {
  round: number;
  label: string;
  score: number;
}

function stageState(round: number, roundReached: number): "cleared" | "cut" | "unreached" {
  if (round < roundReached) return "cleared";
  if (round === roundReached) return roundReached >= 3 ? "cleared" : "cut";
  return "unreached";
}

export function PipelineViz({ candidate }: { candidate: CandidateResult }) {
  const stages: Stage[] = [
    { round: 1, label: "Round 1 · Dense screen", score: candidate.provisional_score },
    { round: 2, label: "Round 2 · Skill match", score: candidate.skill_match_score },
    { round: 3, label: "Round 3 · Verified", score: candidate.skill_based_ats_score },
  ];

  return (
    <div className="flex items-center gap-2">
      {stages.map((stage, i) => {
        const state = stageState(stage.round, candidate.round_reached);
        return (
          <div key={stage.round} className="flex flex-1 items-center gap-2">
            <div
              className={cn(
                "flex flex-1 flex-col items-center gap-1 rounded-lg border p-3",
                state === "cleared" && "border-emerald-500/30 bg-emerald-500/5",
                state === "cut" && "border-red-500/30 bg-red-500/5",
                state === "unreached" && "border-border/60 bg-muted/30 opacity-50",
              )}
            >
              <div className="flex items-center gap-1.5">
                {state === "cleared" && <Check className="size-3.5 text-emerald-600 dark:text-emerald-400" />}
                {state === "cut" && <X className="size-3.5 text-red-600 dark:text-red-400" />}
                <span className="text-xs font-medium text-muted-foreground">{stage.label}</span>
              </div>
              <span className="text-lg font-semibold tabular-nums text-foreground">
                {state === "unreached" ? "—" : `${Math.round(stage.score)}%`}
              </span>
              {state === "cut" && <span className="text-[0.65rem] text-red-600 dark:text-red-400">Cut here</span>}
            </div>
            {i < stages.length - 1 && <div className="h-px w-3 shrink-0 bg-border" />}
          </div>
        );
      })}
    </div>
  );
}
