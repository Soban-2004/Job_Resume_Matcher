"use client";

import { ArrowLeft, Briefcase, Mail, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreRing } from "@/components/app/score-ring";
import { RequirementVerdictList } from "@/components/app/requirement-verdict-card";
import { DecisionPanel } from "@/components/app/decision-panel";
import { PipelineViz } from "@/components/app/pipeline-viz";
import { EmailComposer } from "@/components/app/email-composer";
import { BlurFadeIn } from "@/components/motion/reveal";
import type { CandidateResult } from "@/lib/types";

export function CandidateDetail({
  candidate,
  jobRole,
  onBack,
}: {
  candidate: CandidateResult;
  jobRole: string;
  onBack: () => void;
}) {
  const displayName = candidate.candidate_name?.trim() || candidate.filename;

  return (
    <BlurFadeIn className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <Button variant="ghost" size="sm" onClick={onBack} className="gap-1.5">
          <ArrowLeft className="size-3.5" />
          Back to shortlist
        </Button>
        <EmailComposer candidate={candidate} jobRole={jobRole} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-semibold text-foreground">{displayName}</h2>
        {candidate.candidate_name && (
          <span className="text-sm text-muted-foreground">{candidate.filename}</span>
        )}
        {candidate.experience_years > 0 && (
          <Badge variant="secondary" className="gap-1.5">
            <Briefcase className="size-3" />
            {candidate.experience_years} {candidate.experience_years === 1 ? "year" : "years"} experience
          </Badge>
        )}
        {candidate.candidate_email && (
          <Badge variant="secondary" className="gap-1.5">
            <Mail className="size-3" />
            {candidate.candidate_email}
          </Badge>
        )}
        {candidate.candidate_phone && (
          <Badge variant="secondary" className="gap-1.5">
            <Phone className="size-3" />
            {candidate.candidate_phone}
          </Badge>
        )}
      </div>

      <Card className="flex flex-wrap items-center justify-around gap-8 p-8">
        <ScoreRing label="Overall Fit" score={candidate.overall_fit_score} />
        <ScoreRing label="Skill-Based ATS Score" score={candidate.skill_based_ats_score} />
      </Card>

      <Card className="flex flex-col gap-3 p-6">
        <h3 className="text-lg font-semibold text-foreground">Pipeline</h3>
        <PipelineViz candidate={candidate} />
      </Card>

      <DecisionPanel candidate={candidate} />

      <Card className="flex flex-col gap-4 p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">Requirement Breakdown</h3>
          <div className="flex gap-2">
            <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
              {candidate.matched_requirements.length} matched
            </Badge>
            <Badge variant="secondary" className="bg-red-500/10 text-red-700 dark:text-red-400">
              {candidate.missing_requirements.length} missing
            </Badge>
          </div>
        </div>
        <RequirementVerdictList verdicts={candidate.requirement_verdicts} />
      </Card>
    </BlurFadeIn>
  );
}
