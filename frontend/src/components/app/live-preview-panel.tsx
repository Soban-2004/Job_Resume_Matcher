"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { CheckCircle2, CircleDashed, XCircle } from "lucide-react";
import { ScoreRing } from "@/components/app/score-ring";
import { cn } from "@/lib/utils";

type SampleStatus = "satisfied" | "partial" | "missing";

const SAMPLE_REQUIREMENTS: { requirement: string; status: SampleStatus }[] = [
  { requirement: "Python", status: "satisfied" },
  { requirement: "FastAPI", status: "satisfied" },
  { requirement: "Docker", status: "partial" },
  { requirement: "AWS", status: "missing" },
];

const SAMPLE_EVIDENCE = "“Built and deployed FastAPI services handling real-time inference...”";

const STATUS_ICON: Record<SampleStatus, React.ReactNode> = {
  satisfied: <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />,
  partial: <CircleDashed className="size-4 shrink-0 text-amber-500" />,
  missing: <XCircle className="size-4 shrink-0 text-red-500/70" />,
};

const STATUS_LABEL: Record<SampleStatus, string> = {
  satisfied: "Matched",
  partial: "Partial",
  missing: "Missing",
};

/** A live, animated sample of what the actual product output looks like --
 * this replaces descriptive marketing copy on the landing page with a real
 * (if fabricated) demo, since showing the product beats describing it. Loops
 * gently on an interval so it reads as "alive" without needing interaction. */
export function LivePreviewPanel() {
  const [cycle, setCycle] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setCycle((c) => c + 1), 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full max-w-sm overflow-hidden rounded-[14px] border border-border bg-card shadow-xl shadow-foreground/5">
      <div className="flex items-center gap-1.5 border-b border-border bg-muted/40 px-3 py-2">
        <span className="size-2 rounded-full bg-red-400/70" />
        <span className="size-2 rounded-full bg-amber-400/70" />
        <span className="size-2 rounded-full bg-emerald-400/70" />
        <span className="ml-2 text-[0.7rem] text-muted-foreground">resume_match.ai</span>
      </div>

      <div className="flex flex-col gap-4 p-5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">Overall Fit</span>
          <span className="text-[0.65rem] text-muted-foreground/70">sample analysis</span>
        </div>

        <div className="flex justify-center">
          <ScoreRing key={cycle} label="" score={92} size={88} />
        </div>

        <div className="flex flex-col gap-1.5">
          {SAMPLE_REQUIREMENTS.map((r, i) => (
            <motion.div
              key={`${cycle}-${r.requirement}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 28, delay: 0.15 + i * 0.12 }}
              className={cn(
                "flex items-center gap-2 rounded-md border border-border/60 px-2.5 py-1.5 text-xs",
                r.status === "missing" && "opacity-70"
              )}
            >
              {STATUS_ICON[r.status]}
              <span className="font-medium text-foreground">{r.requirement}</span>
              <span className="ml-auto text-muted-foreground">{STATUS_LABEL[r.status]}</span>
            </motion.div>
          ))}
        </div>

        <motion.blockquote
          key={`quote-${cycle}`}
          initial={{ opacity: 0, filter: "blur(4px)" }}
          animate={{ opacity: 1, filter: "blur(0px)" }}
          transition={{ delay: 0.7, duration: 0.5 }}
          className="rounded-md border-l-2 border-l-emerald-500/50 bg-muted/40 px-3 py-2 text-[0.7rem] italic text-muted-foreground"
        >
          {SAMPLE_EVIDENCE}
        </motion.blockquote>
      </div>
    </div>
  );
}
