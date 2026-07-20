"use client";

import { Briefcase } from "lucide-react";
import { Card } from "@/components/ui/card";
import { scoreTone, TONE_TEXT, TONE_BG } from "@/lib/score-tone";
import { cn } from "@/lib/utils";
import type { CandidateResult } from "@/lib/types";

function ScoreChip({ label, score }: { label: string; score: number }) {
  const tone = scoreTone(score);
  return (
    <div className={cn("flex flex-col items-center gap-0.5 rounded-lg px-3 py-2", TONE_BG[tone])}>
      <span className={cn("text-lg font-semibold tabular-nums", TONE_TEXT[tone])}>{Math.round(score)}%</span>
      <span className="text-[0.65rem] text-muted-foreground">{label}</span>
    </div>
  );
}

export function CandidateCard({
  candidate,
  rank,
  onClick,
}: {
  candidate: CandidateResult;
  rank: number;
  onClick: () => void;
}) {
  const displayName = candidate.candidate_name?.trim() || candidate.filename;

  return (
    <button type="button" onClick={onClick} className="w-full text-left">
      <Card className="flex h-full flex-col gap-3 p-5 hover:border-primary/40">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
              {rank}
            </span>
            <span className="truncate text-sm font-medium text-foreground">{displayName}</span>
          </div>
        </div>

        {candidate.experience_years > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Briefcase className="size-3.5" />
            {candidate.experience_years} {candidate.experience_years === 1 ? "year" : "years"} experience
          </div>
        )}

        <div className="flex gap-2">
          <ScoreChip label="Overall Fit" score={candidate.overall_fit_score} />
          <ScoreChip label="Skill Fit" score={candidate.skill_based_ats_score} />
        </div>

        <div className="mt-auto flex gap-4 text-xs text-muted-foreground">
          <span>
            <span className="font-medium text-foreground">{candidate.matched_requirements.length}</span> matched
          </span>
          <span>
            <span className="font-medium text-foreground">{candidate.missing_requirements.length}</span> missing
          </span>
        </div>
      </Card>
    </button>
  );
}
