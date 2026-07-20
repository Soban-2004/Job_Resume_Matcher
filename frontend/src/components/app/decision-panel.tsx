import { Check, X } from "lucide-react";
import { Card } from "@/components/ui/card";
import { TONE_BG, TONE_TEXT } from "@/lib/score-tone";
import { buildReasons, buildRisks, buildSummary, recommendationFor } from "@/lib/candidate-insights";
import { cn } from "@/lib/utils";
import type { CandidateResult } from "@/lib/types";

export function DecisionPanel({ candidate }: { candidate: CandidateResult }) {
  const { label, tone } = recommendationFor(candidate);
  const summary = buildSummary(candidate);
  const reasons = buildReasons(candidate);
  const risks = buildRisks(candidate);

  return (
    <Card className="flex flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-foreground">Why this recommendation</h3>
        <span className={cn("rounded-full px-3 py-1 text-sm font-semibold", TONE_BG[tone], TONE_TEXT[tone])}>
          {label}
        </span>
      </div>

      <p className="text-sm leading-relaxed text-muted-foreground">{summary}</p>

      {(reasons.length > 0 || risks.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {reasons.length > 0 && (
            <div className="flex flex-col gap-1.5">
              {reasons.map((r) => (
                <div key={r} className="flex items-start gap-1.5 text-sm text-foreground">
                  <Check className="mt-0.5 size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  {r}
                </div>
              ))}
            </div>
          )}
          {risks.length > 0 && (
            <div className="flex flex-col gap-1.5">
              {risks.map((r) => (
                <div key={r} className="flex items-start gap-1.5 text-sm text-foreground">
                  <X className="mt-0.5 size-3.5 shrink-0 text-red-600 dark:text-red-400" />
                  {r}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
