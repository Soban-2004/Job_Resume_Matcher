import { CheckCircle2, XCircle } from "lucide-react";
import type { JobSeekerPartial } from "@/lib/types";

export function EligibilitySnapshot({ partial }: { partial: JobSeekerPartial }) {
  if (partial.resume_experience_years == null) return null;

  // Reuse the backend's authoritative reasons rather than re-deriving
  // degree-ranking logic on the frontend.
  const reasons = partial.eligibility?.reasons ?? [];
  const expFailed = reasons.some((r) => r.toLowerCase().includes("experience"));
  const degreeFailed = reasons.some((r) => r.toLowerCase().includes("degree"));
  const jdDegree = partial.jd_degree?.highest;
  const resumeDegree = partial.resume_degree?.highest;

  return (
    <div className="animate-in fade-in slide-in-from-top-2 flex flex-col gap-2 rounded-lg border border-border p-4 duration-300">
      <div className="flex items-center gap-2.5 text-sm">
        {expFailed ? (
          <XCircle className="size-4 shrink-0 text-red-500/70" />
        ) : (
          <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
        )}
        <span className="text-foreground">
          <span className="font-medium tabular-nums">{partial.resume_experience_years} years</span> of experience
          {partial.jd_experience_years ? ` (${partial.jd_experience_years} required)` : ""}
        </span>
      </div>
      {jdDegree && (
        <div className="flex items-center gap-2.5 text-sm">
          {degreeFailed ? (
            <XCircle className="size-4 shrink-0 text-red-500/70" />
          ) : (
            <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          )}
          <span className="capitalize text-foreground">
            {resumeDegree ?? "No degree detected"} ({jdDegree} required)
          </span>
        </div>
      )}
    </div>
  );
}
