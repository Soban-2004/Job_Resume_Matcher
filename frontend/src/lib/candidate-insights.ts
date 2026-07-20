import type { CandidateResult, RequirementVerdict } from "@/lib/types";
import type { ScoreTone } from "@/lib/score-tone";

export type Recommendation = "Strong Hire" | "Hire" | "Consider" | "Weak Match";

const RECOMMENDATION_TONE: Record<Recommendation, ScoreTone> = {
  "Strong Hire": "good",
  Hire: "good",
  Consider: "warning",
  "Weak Match": "critical",
};

function topByWeight(verdicts: RequirementVerdict[], satisfied: boolean, limit: number): RequirementVerdict[] {
  return verdicts
    .filter((v) => v.satisfied === satisfied)
    .sort((a, b) => b.weight - a.weight)
    .slice(0, limit);
}

/** Templated, not LLM-generated -- deterministic and free, synthesized purely
 * from the rubric verdicts the round-3 review already produced. */
export function recommendationFor(candidate: CandidateResult): { label: Recommendation; tone: ScoreTone } {
  if (candidate.round_reached < 3) {
    return { label: "Weak Match", tone: "critical" };
  }
  const score = candidate.skill_based_ats_score;
  let label: Recommendation;
  if (score >= 85) label = "Strong Hire";
  else if (score >= 65) label = "Hire";
  else if (score >= 45) label = "Consider";
  else label = "Weak Match";
  return { label, tone: RECOMMENDATION_TONE[label] };
}

export function buildSummary(candidate: CandidateResult): string {
  if (candidate.round_reached < 3) {
    return `${candidate.filename} was not fully reviewed -- it was screened out before the detailed skill verification round.`;
  }

  const strengths = topByWeight(candidate.requirement_verdicts, true, 3).map((v) => v.requirement);
  const gaps = topByWeight(candidate.requirement_verdicts, false, 2).map((v) => v.requirement);

  const total = candidate.requirement_verdicts.length;
  const matched = candidate.matched_requirements.length;

  let summary = `Satisfies ${matched}/${total} requirements (${Math.round(candidate.skill_based_ats_score)}% skill fit)`;
  if (strengths.length > 0) {
    summary += `, with strong alignment on ${strengths.join(", ")}`;
  }
  summary += ".";
  if (gaps.length > 0) {
    summary += ` Missing ${gaps.join(" and ")}.`;
  }
  summary += ` Overall fit against the role is ${Math.round(candidate.overall_fit_score)}%.`;
  return summary;
}

export function buildReasons(candidate: CandidateResult): string[] {
  return topByWeight(candidate.requirement_verdicts, true, 4).map((v) => v.requirement);
}

export function buildRisks(candidate: CandidateResult): string[] {
  return topByWeight(candidate.requirement_verdicts, false, 4).map((v) => v.requirement);
}
