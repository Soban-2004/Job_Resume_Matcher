// Status colors are reserved for state, always paired with a label/number --
// never color-alone. Three fixed bands so a score's meaning is legible at a
// glance without requiring exact-number comparison.
export type ScoreTone = "good" | "warning" | "critical";

export function scoreTone(score: number): ScoreTone {
  if (score >= 75) return "good";
  if (score >= 40) return "warning";
  return "critical";
}

export const TONE_TEXT: Record<ScoreTone, string> = {
  good: "text-emerald-600 dark:text-emerald-400",
  warning: "text-amber-600 dark:text-amber-400",
  critical: "text-red-600 dark:text-red-400",
};

export const TONE_RING: Record<ScoreTone, string> = {
  good: "stroke-emerald-500",
  warning: "stroke-amber-500",
  critical: "stroke-red-500",
};

export const TONE_BG: Record<ScoreTone, string> = {
  good: "bg-emerald-500/10",
  warning: "bg-amber-500/10",
  critical: "bg-red-500/10",
};
