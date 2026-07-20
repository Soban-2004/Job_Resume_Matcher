"use client";

import { useEffect, useState } from "react";
import { FileText, Plus, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { StaggerGroup, StaggerItem } from "@/components/motion/reveal";
import { scoreTone, TONE_TEXT } from "@/lib/score-tone";
import { listReports, listResumes } from "@/lib/api";
import { GRADIENT_CTA } from "@/lib/category-theme";
import { cn } from "@/lib/utils";
import type { ReportSummary, ResumeLibraryItem } from "@/lib/types";

export function JobSeekerDashboard({
  onNewAnalysis,
  onViewReport,
}: {
  onNewAnalysis: () => void;
  onViewReport: (reportId: string) => void;
}) {
  const [resumes, setResumes] = useState<ResumeLibraryItem[] | null>(null);
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listResumes(), listReports()])
      .then(([r, rep]) => {
        setResumes(r);
        setReports(rep);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load your dashboard."));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <Button size="lg" className={cn("w-fit gap-2", GRADIENT_CTA)} onClick={onNewAnalysis}>
        <Plus className="size-4" />
        New Analysis
      </Button>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card className="flex flex-col gap-3 p-6">
        <h2 className="text-sm font-medium text-muted-foreground">Your Resumes</h2>
        {resumes === null && !error && (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-5 w-1/2" />
          </div>
        )}
        {resumes && resumes.length === 0 && (
          <p className="text-sm text-muted-foreground">No resumes uploaded yet.</p>
        )}
        {resumes && resumes.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {resumes.map((r) => (
              <li key={r.id} className="flex items-center gap-2 text-sm text-foreground/80">
                <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{r.filename}</span>
                <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                  {new Date(r.created_at).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="flex flex-col gap-3 p-6">
        <h2 className="text-sm font-medium text-muted-foreground">Recent Reports</h2>
        {reports === null && !error && (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        )}
        {reports && reports.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No saved reports yet -- run a new analysis to build your history.
          </p>
        )}
        {reports && reports.length > 0 && (
          <StaggerGroup className="flex flex-col gap-2">
            {reports.map((r) => {
              const tone = scoreTone(r.skill_based_ats_score);
              return (
                <StaggerItem key={r.id}>
                  <button
                    type="button"
                    onClick={() => onViewReport(r.id)}
                    className="flex w-full items-center gap-3 rounded-lg border border-border px-4 py-3 text-left transition-colors hover:border-primary/40"
                  >
                    <Sparkles className="size-4 shrink-0 text-primary" />
                    <div className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-sm font-medium text-foreground">{r.job_role}</span>
                      <span className="truncate text-xs text-muted-foreground">{r.resume_filename}</span>
                    </div>
                    <span className={cn("shrink-0 text-sm font-semibold tabular-nums", TONE_TEXT[tone])}>
                      {Math.round(r.skill_based_ats_score)}%
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {new Date(r.created_at).toLocaleDateString()}
                    </span>
                  </button>
                </StaggerItem>
              );
            })}
          </StaggerGroup>
        )}
      </Card>
    </div>
  );
}
