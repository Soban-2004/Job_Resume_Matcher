import Link from "next/link";
import { ArrowRight, Compass, Users } from "lucide-react";
import { Card } from "@/components/ui/card";
import { LivePreviewPanel } from "@/components/app/live-preview-panel";
import { GRADIENT_CTA } from "@/lib/category-theme";
import { cn } from "@/lib/utils";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-16 px-6 py-20">
      <div className="grid items-center gap-12 lg:grid-cols-[1.1fr_1fr]">
        <div className="flex flex-col gap-5">
          <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
            Find the resume that actually fits.
          </h1>
          <p className="max-w-lg text-balance text-lg text-muted-foreground">
            Not the one with the most keywords. Every match is cited to the exact resume
            evidence that supports it.
          </p>

          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href="/job-seeker"
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all hover:-translate-y-0.5",
                GRADIENT_CTA
              )}
            >
              <Compass className="size-4" />
              Analyze my resume
              <ArrowRight className="size-4" />
            </Link>
            <Link
              href="/recruiter"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-all hover:-translate-y-0.5 hover:border-blue-500/40"
            >
              <Users className="size-4 text-blue-600 dark:text-blue-400" />
              Rank candidates
            </Link>
          </div>
        </div>

        <div className="flex justify-center lg:justify-end">
          <LivePreviewPanel />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="flex flex-col gap-2 rounded-[14px] border-l-2 border-l-violet-500/50 p-5">
          <div className="flex items-center gap-2">
            <Compass className="size-4 text-violet-600 dark:text-violet-400" />
            <h2 className="text-sm font-semibold text-foreground">For Job Seekers</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Evidence-backed fit score, a cited requirement breakdown, a tailored cover
            letter, and concrete resume improvements.
          </p>
        </Card>

        <Card className="flex flex-col gap-2 rounded-[14px] border-l-2 border-l-blue-500/50 p-5">
          <div className="flex items-center gap-2">
            <Users className="size-4 text-blue-600 dark:text-blue-400" />
            <h2 className="text-sm font-semibold text-foreground">For Recruiters</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Upload a job description and a batch of resumes for a ranked shortlist, each
            candidate scored against every requirement, live as it processes.
          </p>
        </Card>
      </div>
    </main>
  );
}
