import { CheckCircle2, GraduationCap, XCircle } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import type { RequirementVerdict } from "@/lib/types";

export function VerdictAccordionItem({
  v,
  itemKey,
  staggerIndex = 0,
}: {
  v: RequirementVerdict;
  itemKey: string;
  staggerIndex?: number;
}) {
  return (
    <AccordionItem
      value={itemKey}
      style={{ animationDelay: `${Math.min(staggerIndex, 12) * 60}ms` }}
      className="animate-in fade-in slide-in-from-top-1 rounded-lg border border-border px-4 duration-300 transition-colors hover:border-primary/30 data-[state=open]:bg-accent/30"
    >
      <AccordionTrigger className="py-3 hover:no-underline">
        <div className="flex flex-1 items-center gap-3 pr-2">
          {v.satisfied ? (
            <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <XCircle className="size-4 shrink-0 text-red-500/70" />
          )}
          <span className="text-left text-sm font-medium capitalize text-foreground">{v.requirement}</span>
          <Badge variant="secondary" className="ml-auto shrink-0 text-xs font-normal">
            weight {v.weight.toFixed(1)}
          </Badge>
        </div>
      </AccordionTrigger>
      <AccordionContent className="flex flex-col gap-3 pb-4 text-sm">
        <p className="text-muted-foreground">{v.justification}</p>
        {v.evidence.length > 0 ? (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Cited evidence
            </span>
            {v.evidence.map((snippet, i) => (
              <blockquote
                key={i}
                className="rounded-md border-l-2 border-primary/40 bg-muted/50 px-3 py-1.5 text-sm italic text-foreground/80"
              >
                &ldquo;{snippet}&rdquo;
              </blockquote>
            ))}
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">No supporting evidence found in the resume.</span>
        )}
        {!v.satisfied && v.suggested_certification && (
          <div className="flex items-start gap-2 rounded-md bg-primary/5 px-3 py-2 text-sm text-foreground">
            <GraduationCap className="mt-0.5 size-4 shrink-0 text-primary" />
            <span>
              <span className="font-medium">Consider: </span>
              {v.suggested_certification}
            </span>
          </div>
        )}
      </AccordionContent>
    </AccordionItem>
  );
}

export function RequirementVerdictList({ verdicts }: { verdicts: RequirementVerdict[] }) {
  const sorted = [...verdicts].sort((a, b) => {
    if (a.satisfied !== b.satisfied) return a.satisfied ? -1 : 1;
    return b.weight - a.weight;
  });

  return (
    <Accordion multiple className="flex flex-col gap-2">
      {sorted.map((v, i) => (
        <VerdictAccordionItem key={`${v.requirement}-${i}`} v={v} itemKey={`${v.requirement}-${i}`} staggerIndex={i} />
      ))}
    </Accordion>
  );
}
