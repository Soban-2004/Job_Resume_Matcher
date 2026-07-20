"use client";

import { scoreTone, TONE_RING, TONE_TEXT } from "@/lib/score-tone";
import { useCountUp } from "@/lib/use-count-up";
import { cn } from "@/lib/utils";

interface ScoreRingProps {
  label: string;
  score: number;
  size?: number;
  provisional?: boolean;
}

export function ScoreRing({ label, score, size = 112, provisional = false }: ScoreRingProps) {
  const animated = useCountUp(score);
  const tone = scoreTone(animated);
  const clamped = Math.max(0, Math.min(100, animated));
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={8}
            fill="none"
            className="stroke-muted"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={8}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={cn(TONE_RING[tone], "transition-[stroke-dashoffset] duration-300 ease-out")}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn("text-2xl font-semibold tabular-nums", TONE_TEXT[tone])}>
            {Math.round(clamped)}%
          </span>
        </div>
      </div>
      {label && (
        <span className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
          {provisional && (
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/60" />
              <span className="relative inline-flex size-1.5 rounded-full bg-primary" />
            </span>
          )}
          {label}
          {provisional && <span className="text-xs text-muted-foreground/70">(so far)</span>}
        </span>
      )}
    </div>
  );
}
