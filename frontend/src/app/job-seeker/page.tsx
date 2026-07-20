"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, Compass, RotateCcw, Sparkles, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { FileDropzone } from "@/components/app/file-dropzone";
import { ScoreRing } from "@/components/app/score-ring";
import { StageProgressList } from "@/components/app/stage-progress";
import { ActivityTicker } from "@/components/app/activity-ticker";
import { EligibilitySnapshot } from "@/components/app/eligibility-snapshot";
import { LiveRequirementChecklist } from "@/components/app/live-requirement-checklist";
import { AnalysisResultView } from "@/components/app/analysis-result-view";
import { JobSeekerDashboard } from "@/components/app/job-seeker-dashboard";
import { BlurFadeIn } from "@/components/motion/reveal";
import { GRADIENT_CTA } from "@/lib/category-theme";
import { createJobSeekerJob, getJobSeekerJob, getReport, stopJobSeekerJob } from "@/lib/api";
import { useJobPolling } from "@/lib/use-job-polling";
import { cn } from "@/lib/utils";
import type { JdRequirement, JobSeekerAnalysisResponse, RequirementVerdict } from "@/lib/types";

function computeProvisionalScore(jdRequirements: JdRequirement[], verdicts: RequirementVerdict[]): number {
  const totalWeight = jdRequirements.reduce((sum, r) => sum + r.weight, 0);
  if (totalWeight === 0) return 0;
  const satisfiedWeight = verdicts.filter((v) => v.satisfied).reduce((sum, v) => sum + v.weight, 0);
  return (satisfiedWeight / totalWeight) * 100;
}

type View = "dashboard" | "form" | "report";

export default function JobSeekerPage() {
  const [view, setView] = useState<View>("dashboard");
  const [viewedReport, setViewedReport] = useState<JobSeekerAnalysisResponse | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const [resume, setResume] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<File | null>(null);
  const [jobRole, setJobRole] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [stopping, setStopping] = useState(false);

  const { status, pollError } = useJobPolling(jobId, getJobSeekerJob);

  const canSubmit = resume && jobDescription && jobRole.trim().length > 0 && !submitting;

  async function handleSubmit() {
    if (!resume || !jobDescription) return;
    setSubmitError(null);
    setSubmitting(true);
    try {
      const id = await createJobSeekerJob(resume, jobDescription, jobRole.trim());
      setJobId(id);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to start analysis");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleViewReport(reportId: string) {
    setReportError(null);
    setViewedReport(null);
    setView("report");
    try {
      const report = await getReport(reportId);
      setViewedReport(report);
    } catch (e) {
      setReportError(e instanceof Error ? e.message : "Failed to load report.");
    }
  }

  async function handleStop() {
    if (!jobId) return;
    setStopping(true);
    try {
      await stopJobSeekerJob(jobId);
    } finally {
      setStopping(false);
    }
  }

  function handleReset() {
    setJobId(null);
    setResume(null);
    setJobDescription(null);
    setJobRole("");
    setSubmitError(null);
    setViewedReport(null);
    setView("dashboard");
  }

  const result = status?.result as JobSeekerAnalysisResponse | null;
  // `jobId &&` matters here: useJobPolling doesn't clear its last `status`
  // when jobId resets to null (e.g. "Start over"), so without this guard the
  // stale completed-job status would keep the results view rendered
  // underneath the dashboard instead of actually returning to it.
  const isRunning =
    jobId && status && status.state !== "completed" && status.state !== "failed" && status.state !== "stopped";
  const jdRequirements = status?.partial.jd_requirements ?? [];
  const showFinalResult =
    jobId && (status?.state === "completed" || status?.state === "stopped") && result && result.eligibility.eligible;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-12">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Home
        </Link>
        <div className="flex items-center gap-2">
          {isRunning && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleStop}
              disabled={stopping || status?.state === "stopped"}
              className="gap-1.5"
            >
              <Square className="size-3.5" />
              {stopping ? "Stopping..." : "Stop"}
            </Button>
          )}
          {(jobId || view !== "dashboard") && (
            <Button variant="ghost" size="sm" onClick={handleReset} className="gap-1.5">
              <RotateCcw className="size-3.5" />
              {jobId ? "Start over" : "Back to dashboard"}
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Compass className="size-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Job Seeker Analysis</h1>
          <p className="text-sm text-muted-foreground">
            Upload your resume and the job description you&apos;re targeting.
          </p>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {!jobId && view === "dashboard" && (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -8, filter: "blur(6px)" }}
            transition={{ type: "spring", stiffness: 280, damping: 30 }}
          >
            <JobSeekerDashboard onNewAnalysis={() => setView("form")} onViewReport={handleViewReport} />
          </motion.div>
        )}

        {!jobId && view === "report" && (
          <motion.div
            key="report"
            initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -8, filter: "blur(6px)" }}
            transition={{ type: "spring", stiffness: 280, damping: 30 }}
          >
            {reportError && (
              <Alert variant="destructive">
                <AlertDescription>{reportError}</AlertDescription>
              </Alert>
            )}
            {viewedReport && <AnalysisResultView result={viewedReport} />}
          </motion.div>
        )}

        {!jobId && view === "form" && (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -8, filter: "blur(6px)" }}
            transition={{ type: "spring", stiffness: 280, damping: 30 }}
          >
            <Card className="flex flex-col gap-6 p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <FileDropzone
                  label="Resume"
                  hint="PDF, DOCX, or TXT"
                  accept=".pdf,.docx,.txt"
                  file={resume}
                  onChange={setResume}
                />
                <FileDropzone
                  label="Job Description"
                  hint="PDF, DOCX, or TXT"
                  accept=".pdf,.docx,.txt"
                  file={jobDescription}
                  onChange={setJobDescription}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="job-role">Job role</Label>
                <Input
                  id="job-role"
                  placeholder="e.g. Data Analyst, Backend Engineer"
                  value={jobRole}
                  onChange={(e) => setJobRole(e.target.value)}
                />
              </div>
              {submitError && (
                <Alert variant="destructive">
                  <AlertDescription>{submitError}</AlertDescription>
                </Alert>
              )}
              <Button onClick={handleSubmit} disabled={!canSubmit} size="lg" className={cn("gap-2", GRADIENT_CTA)}>
                <Sparkles className="size-4" />
                {submitting ? "Starting analysis..." : "Analyze Resume Match"}
              </Button>
            </Card>
          </motion.div>
        )}

        {isRunning && (
          <motion.div
            key="running"
            className="flex flex-col gap-6"
            initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -8, filter: "blur(6px)" }}
            transition={{ type: "spring", stiffness: 280, damping: 30 }}
          >
            <Card className="flex flex-col gap-4 p-6">
              <h2 className="text-sm font-medium text-muted-foreground">Analyzing your resume&hellip;</h2>
              <StageProgressList stages={status.stages} />
              <ActivityTicker text={status.current_activity} />
            </Card>

            <EligibilitySnapshot partial={status.partial} />

            {jdRequirements.length > 0 && (
              <BlurFadeIn>
                <Card className="flex flex-wrap items-center justify-around gap-8 p-8">
                  <ScoreRing
                    label="Skill-Based ATS Score"
                    score={computeProvisionalScore(jdRequirements, status.verdicts)}
                    provisional
                  />
                </Card>
              </BlurFadeIn>
            )}

            {jdRequirements.length > 0 && (
              <Card className="flex flex-col gap-4 p-6">
                <h2 className="text-lg font-semibold text-foreground">Requirement Breakdown</h2>
                <LiveRequirementChecklist jdRequirements={jdRequirements} verdicts={status.verdicts} />
              </Card>
            )}

            {status.partial.cover_letter && (
              <BlurFadeIn>
                <Card className="flex flex-col gap-3 p-6">
                  <h2 className="text-lg font-semibold text-foreground">Tailored Cover Letter</h2>
                  <p className="whitespace-pre-line text-sm leading-relaxed text-foreground/80">
                    {status.partial.cover_letter}
                  </p>
                </Card>
              </BlurFadeIn>
            )}
          </motion.div>
        )}

        {showFinalResult && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ type: "spring", stiffness: 260, damping: 28 }}
          >
            <AnalysisResultView result={result} />
          </motion.div>
        )}
      </AnimatePresence>

      {pollError && (
        <Alert variant="destructive">
          <AlertTitle>Connection error</AlertTitle>
          <AlertDescription>{pollError}</AlertDescription>
        </Alert>
      )}

      {status?.state === "failed" && (
        <Alert variant="destructive">
          <AlertTitle>Analysis failed</AlertTitle>
          <AlertDescription>{status.error}</AlertDescription>
        </Alert>
      )}

      {status?.state === "stopped" && (
        <Alert>
          <AlertTitle>Stopped early</AlertTitle>
          <AlertDescription>
            The analysis was stopped before finishing. Results below reflect whatever was completed
            before the stop.
          </AlertDescription>
        </Alert>
      )}

      {(status?.state === "completed" || status?.state === "stopped") && result && !result.eligibility.eligible && (
        <Alert variant="destructive">
          <AlertTitle>Not eligible for this role</AlertTitle>
          <AlertDescription>
            <ul className="list-disc pl-4">
              {result.eligibility.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
    </main>
  );
}
