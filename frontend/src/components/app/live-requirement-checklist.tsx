"use client";

import { Circle } from "lucide-react";
import { Accordion } from "@/components/ui/accordion";
import { VerdictAccordionItem } from "@/components/app/requirement-verdict-card";
import type { JdRequirement, RequirementVerdict } from "@/lib/types";

interface LiveRequirementChecklistProps {
  jdRequirements: JdRequirement[];
  verdicts: RequirementVerdict[];
}

export function LiveRequirementChecklist({ jdRequirements, verdicts }: LiveRequirementChecklistProps) {
  const verdictMap = new Map(verdicts.map((v) => [v.requirement, v]));
  const matchedCount = verdicts.filter((v) => v.satisfied).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-foreground">
          {verdicts.length} of {jdRequirements.length} checked
        </span>
        {verdicts.length > 0 && (
          <span className="text-muted-foreground">{matchedCount} matched so far</span>
        )}
      </div>
      <Accordion multiple className="flex flex-col gap-2">
        {jdRequirements.map((req, i) => {
          const verdict = verdictMap.get(req.requirement);
          const itemKey = `${req.requirement}-${i}`;
          if (!verdict) {
            return (
              <div
                key={itemKey}
                className="flex items-center gap-3 rounded-lg border border-dashed border-border px-4 py-3 opacity-60"
              >
                <Circle className="size-4 shrink-0 animate-pulse text-muted-foreground" />
                <span className="text-sm capitalize text-muted-foreground">{req.requirement}</span>
              </div>
            );
          }
          return <VerdictAccordionItem key={itemKey} v={verdict} itemKey={itemKey} />;
        })}
      </Accordion>
    </div>
  );
}
