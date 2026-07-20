"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, ChevronDown, Plus, Square, Trophy, Users, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { MultiFileDropzone } from "@/components/app/multi-file-dropzone";
import { CandidateProgressList } from "@/components/app/candidate-progress";
import { CandidateCard } from "@/components/app/candidate-card";
import { CandidateDetail } from "@/components/app/candidate-detail";
import { RoundApprovalCard } from "@/components/app/round-approval";
import { StaggerGroup, StaggerItem } from "@/components/motion/reveal";
import {
  approveNextRound,
  createProjectBatch,
  getProject,
  getRecruiterJob,
  stopRecruiterJob,
} from "@/lib/api";
import { useJobPolling } from "@/lib/use-job-polling";
import { cn } from "@/lib/utils";
import { GRADIENT_CTA, ROUND_THEME } from "@/lib/category-theme";
import type { CandidateResult, ProjectDetail } from "@/lib/types";

function roundCutLabel(candidate: CandidateResult): string {
  if (!candidate.eligible) return "Not eligible";
  if (candidate.round_reached === 1) return "Cut at round 1";
  if (candidate.round_reached === 2) return "Cut at round 2";
  return "Not advancing";
}

function roundBadgeTheme(candidate: CandidateResult): string {
  if (!candidate.eligible) return "bg-muted text-muted-foreground";
  if (candidate.round_reached === 1) return "bg-slate-500/15 text-slate-700 dark:text-slate-300";
  return "bg-violet-500/15 text-violet-700 dark:text-violet-300";
}

export default function ProjectWorkspacePage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [resumes, setResumes] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [showNotAdvancing, setShowNotAdvancing] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateResult | null>(null);

  const { status, pollError } = useJobPolling(jobId, getRecruiterJob);
  const isActive = status && status.state !== "completed" && status.state !== "failed" && status.state !== "stopped";

  const loadProject = useCallback(() => {
    return getProject(projectId)
      .then(setProject)
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load project."));
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  // Once a batch run finishes, the backend has already persisted its
  // candidates into the project -- refetch to pick up the merged list, then
  // drop the ephemeral job state so the page falls back to showing the
  // project's persisted view instead of a stale one-off result. The resets
  // happen inside the refetch's own callback (an external-system response),
  // not synchronously in the effect body, so this isn't a cascading-render
  // setState-in-effect.
  useEffect(() => {
    if (status?.state === "completed" || status?.state === "stopped") {
      loadProject().then(() => {
        setJobId(null);
        setAdding(false);
        setResumes([]);
      });
    }
  }, [status?.state, loadProject]);

  async function handleSubmit() {
    if (resumes.length === 0) return;
    setSubmitError(null);
    setSubmitting(true);
    try {
      const id = await createProjectBatch(projectId, resumes);
      setJobId(id);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Failed to start analysis.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove() {
    if (!jobId) return;
    await approveNextRound(jobId);
  }

  async function handleStop() {
    if (!jobId) return;
    setStopping(true);
    try {
      await stopRecruiterJob(jobId);
    } finally {
      setStopping(false);
    }
  }

  if (loadError) {
    return (
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-12">
        <Alert variant="destructive">
          <AlertDescription>{loadError}</AlertDescription>
        </Alert>
      </main>
    );
  }

  if (!project) {
    return (
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-12">
        <p className="text-sm text-muted-foreground">Loading project...</p>
      </main>
    );
  }

  const advancing = project.candidates.filter((c) => c.eligible && c.shortlisted);
  const notAdvancing = project.candidates.filter((c) => !c.eligible || !c.shortlisted);

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-12">
      <div className="flex items-center justify-between">
        <Link href="/recruiter" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" />
          All projects
        </Link>
        {isActive && (
          <Button variant="destructive" size="sm" onClick={handleStop} disabled={stopping} className="gap-1.5">
            <Square className="size-3.5" />
            {stopping ? "Stopping..." : "Stop"}
          </Button>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Users className="size-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{project.name}</h1>
          <p className="text-sm text-muted-foreground">{project.job_role}</p>
        </div>
      </div>

      {selectedCandidate ? (
        <CandidateDetail
          candidate={selectedCandidate}
          jobRole={project.job_role}
          onBack={() => setSelectedCandidate(null)}
        />
      ) : (
        <>
          {!jobId && !adding && (
            <Button size="lg" className={cn("w-fit gap-2", GRADIENT_CTA)} onClick={() => setAdding(true)}>
              <Plus className="size-4" />
              Evaluate More Candidates
            </Button>
          )}

          {!jobId && adding && (
            <Card className="flex flex-col gap-6 p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-foreground">Add Candidates</h2>
                <Button variant="ghost" size="icon-sm" onClick={() => setAdding(false)}>
                  <X className="size-3.5" />
                </Button>
              </div>
              <MultiFileDropzone
                label="Candidate resumes"
                hint="PDF, DOCX, or TXT -- upload as many as you like"
                accept=".pdf,.docx,.txt"
                files={resumes}
                onChange={setResumes}
              />
              {submitError && (
                <Alert variant="destructive">
                  <AlertDescription>{submitError}</AlertDescription>
                </Alert>
              )}
              <Button
                onClick={handleSubmit}
                disabled={resumes.length === 0 || submitting}
                size="lg"
                className={cn("gap-2", GRADIENT_CTA)}
              >
                {submitting
                  ? "Starting analysis..."
                  : `Analyze ${resumes.length || ""} Candidate${resumes.length === 1 ? "" : "s"}`}
              </Button>
            </Card>
          )}

          {jobId && status && status.state === "running" && (
            <Card className="flex flex-col gap-4 p-6">
              <h2 className="text-sm font-medium text-muted-foreground">Ranking candidates&hellip;</h2>
              <CandidateProgressList candidates={status.candidates} />
            </Card>
          )}

          {jobId && status && status.state === "awaiting_approval" && status.pending_approval && (
            <Card className="p-6">
              <RoundApprovalCard summary={status.pending_approval} onApprove={handleApprove} />
            </Card>
          )}

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

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 28 }}
            className="flex flex-col gap-6"
          >
            <Card className="flex flex-col gap-4 p-6">
              <div className="flex items-center gap-2">
                <div className="flex size-8 items-center justify-center rounded-lg bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400">
                  <Trophy className="size-4" />
                </div>
                <h2 className="text-lg font-semibold text-foreground">Shortlisted</h2>
                <Badge variant="secondary" className="ml-auto bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300">
                  {advancing.length} advancing
                </Badge>
              </div>

              {advancing.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No candidates yet -- evaluate resumes to build this project&apos;s shortlist.
                </p>
              ) : (
                <StaggerGroup className="grid gap-4 sm:grid-cols-2">
                  {advancing.map((candidate, rank) => (
                    <StaggerItem key={`${candidate.filename}-${rank}`}>
                      <CandidateCard
                        candidate={candidate}
                        rank={rank + 1}
                        onClick={() => setSelectedCandidate(candidate)}
                      />
                    </StaggerItem>
                  ))}
                </StaggerGroup>
              )}
            </Card>

            {notAdvancing.length > 0 && (
              <Card className="flex flex-col gap-3 p-6">
                <button
                  type="button"
                  onClick={() => setShowNotAdvancing((v) => !v)}
                  className="flex items-center justify-between text-left"
                >
                  <span className="text-sm font-medium text-muted-foreground">
                    Not Advancing ({notAdvancing.length})
                  </span>
                  <ChevronDown
                    className={cn(
                      "size-4 text-muted-foreground transition-transform duration-200",
                      showNotAdvancing && "rotate-180"
                    )}
                  />
                </button>
                <AnimatePresence initial={false}>
                  {showNotAdvancing && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ type: "spring", stiffness: 300, damping: 32 }}
                      className="overflow-hidden"
                    >
                      <Accordion multiple className="flex flex-col gap-2 pt-1">
                        {notAdvancing.map((candidate, i) => (
                          <AccordionItem
                            key={`${candidate.filename}-na-${i}`}
                            value={`${candidate.filename}-na-${i}`}
                            className={cn(
                              "rounded-lg border px-4 transition-colors duration-200 data-[state=open]:bg-accent/20",
                              candidate.eligible ? ROUND_THEME[candidate.round_reached] : "border-border/60 bg-muted/20"
                            )}
                          >
                            <AccordionTrigger className="py-2.5 hover:no-underline">
                              <div className="flex flex-1 items-center gap-3 pr-2">
                                <span className="truncate text-left text-sm text-muted-foreground">
                                  {candidate.filename}
                                </span>
                                <Badge variant="secondary" className={cn("ml-auto shrink-0", roundBadgeTheme(candidate))}>
                                  {roundCutLabel(candidate)}
                                </Badge>
                              </div>
                            </AccordionTrigger>
                            <AccordionContent className="pb-3 text-sm text-muted-foreground">
                              {!candidate.eligible ? (
                                <ul className="list-disc pl-4">
                                  {candidate.reasons.map((r) => (
                                    <li key={r}>{r}</li>
                                  ))}
                                </ul>
                              ) : candidate.round_reached === 1 ? (
                                <p>
                                  Round 1 dense-similarity prescreen only (
                                  {Math.round(candidate.provisional_score)}% provisional fit) -- didn&apos;t
                                  make the round 2 shortlist, so no skill-match or detailed review was run.
                                </p>
                              ) : (
                                <p>
                                  Reached round 2&apos;s skill-match narrowing (
                                  {Math.round(candidate.skill_match_score)}% skill-match fit, from a round 1
                                  prescreen of {Math.round(candidate.provisional_score)}%) but didn&apos;t
                                  make the final shortlist for detailed per-requirement LLM review.
                                </p>
                              )}
                            </AccordionContent>
                          </AccordionItem>
                        ))}
                      </Accordion>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            )}
          </motion.div>
        </>
      )}
    </main>
  );
}
