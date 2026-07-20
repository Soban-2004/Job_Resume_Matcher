import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StageStatus } from "@/lib/types";

export function StageProgressList({ stages }: { stages: StageStatus[] }) {
  return (
    <ul className="flex flex-col gap-1">
      {stages.map((stage) => (
        <li key={stage.key} className="flex items-center gap-3 py-1.5">
          <span
            className={cn(
              "flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px]",
              stage.state === "done" && "border-emerald-500 bg-emerald-500 text-white",
              stage.state === "running" && "border-primary text-primary",
              stage.state === "pending" && "border-border text-transparent"
            )}
          >
            {stage.state === "done" && <Check className="size-3" />}
            {stage.state === "running" && <Loader2 className="size-3 animate-spin" />}
          </span>
          <span
            className={cn(
              "text-sm transition-colors",
              stage.state === "pending" && "text-muted-foreground",
              stage.state === "running" && "font-medium text-foreground",
              stage.state === "done" && "text-foreground/70"
            )}
          >
            {stage.label}
          </span>
        </li>
      ))}
    </ul>
  );
}
