"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { downloadOptimizedResumePdf } from "@/lib/api";
import { GRADIENT_CTA } from "@/lib/category-theme";
import type { OptimizedResume } from "@/lib/types";

export function OptimizedResumeView({ resume }: { resume: OptimizedResume }) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload() {
    setDownloading(true);
    setError(null);
    try {
      await downloadOptimizedResumePdf(resume);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate PDF.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card className="flex flex-col gap-5 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Optimized Resume</h2>
          <p className="text-xs text-muted-foreground">
            Tailored to this job description. Every claim traces back to your original resume.
          </p>
        </div>
        <Button size="sm" className={GRADIENT_CTA} disabled={downloading} onClick={handleDownload}>
          {downloading ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" />}
          {downloading ? "Generating..." : "Download PDF"}
        </Button>
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="flex flex-col gap-4 rounded-lg border border-border bg-muted/20 p-5">
        {resume.full_name && <h3 className="text-base font-semibold text-foreground">{resume.full_name}</h3>}
        {resume.contact_line && <p className="text-xs text-muted-foreground">{resume.contact_line}</p>}

        {resume.sections.map((section, i) => (
          <div key={i} className="flex flex-col gap-1.5">
            <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {section.heading}
            </h4>
            <ul className="flex flex-col gap-1">
              {section.lines.map((line, j) => (
                <li key={j} className="flex gap-2 text-sm text-foreground/80">
                  <span className="text-primary">&bull;</span>
                  {line}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  );
}
