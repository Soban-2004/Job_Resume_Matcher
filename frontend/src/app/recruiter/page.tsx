"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FolderKanban, Plus, Users, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FileDropzone } from "@/components/app/file-dropzone";
import { StaggerGroup, StaggerItem } from "@/components/motion/reveal";
import { createProject, listProjects } from "@/lib/api";
import { GRADIENT_CTA } from "@/lib/category-theme";
import { cn } from "@/lib/utils";
import type { ProjectSummary } from "@/lib/types";

export default function RecruiterDashboardPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const [name, setName] = useState("");
  const [jobRole, setJobRole] = useState("");
  const [jobDescription, setJobDescription] = useState<File | null>(null);
  const [numVacancies, setNumVacancies] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const router = useRouter();

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load projects."));
  }, []);

  const canCreate = name.trim() && jobRole.trim() && jobDescription && !creating;

  async function handleCreate() {
    if (!jobDescription) return;
    setCreateError(null);
    setCreating(true);
    try {
      const vacancies = numVacancies.trim() ? Number(numVacancies) : undefined;
      const project = await createProject(name.trim(), jobRole.trim(), jobDescription, vacancies);
      router.push(`/recruiter/${project.id}`);
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "Failed to create project.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-12">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Users className="size-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Recruitment Projects</h1>
          <p className="text-sm text-muted-foreground">
            Each project is an isolated hiring campaign -- create one per role you&apos;re hiring for.
          </p>
        </div>
      </div>

      {!showCreate ? (
        <Button size="lg" className={cn("w-fit gap-2", GRADIENT_CTA)} onClick={() => setShowCreate(true)}>
          <Plus className="size-4" />
          New Project
        </Button>
      ) : (
        <Card className="flex flex-col gap-5 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">New Recruitment Project</h2>
            <Button variant="ghost" size="icon-sm" onClick={() => setShowCreate(false)}>
              <X className="size-3.5" />
            </Button>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="project-name">Project name</Label>
            <Input
              id="project-name"
              placeholder="e.g. AI Engineer Hiring"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="job-role">Job role</Label>
            <Input
              id="job-role"
              placeholder="e.g. AI Engineer"
              value={jobRole}
              onChange={(e) => setJobRole(e.target.value)}
            />
          </div>

          <FileDropzone
            label="Job Description"
            hint="PDF, DOCX, or TXT"
            accept=".pdf,.docx,.txt"
            file={jobDescription}
            onChange={setJobDescription}
          />

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="num-vacancies">Number of vacancies (optional)</Label>
            <Input
              id="num-vacancies"
              type="number"
              min={1}
              placeholder="e.g. 2"
              value={numVacancies}
              onChange={(e) => setNumVacancies(e.target.value)}
              className="max-w-[10rem]"
            />
          </div>

          {createError && (
            <Alert variant="destructive">
              <AlertDescription>{createError}</AlertDescription>
            </Alert>
          )}

          <Button className={GRADIENT_CTA} disabled={!canCreate} onClick={handleCreate}>
            {creating ? "Creating..." : "Create Project"}
          </Button>
        </Card>
      )}

      {loadError && (
        <Alert variant="destructive">
          <AlertDescription>{loadError}</AlertDescription>
        </Alert>
      )}

      {projects && projects.length > 0 && (
        <StaggerGroup className="grid gap-4 sm:grid-cols-2">
          {projects.map((p) => (
            <StaggerItem key={p.id}>
              <Link href={`/recruiter/${p.id}`}>
                <Card className="flex h-full flex-col gap-3 p-5 hover:border-primary/40">
                  <div className="flex items-center gap-2">
                    <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-400">
                      <FolderKanban className="size-3.5" />
                    </div>
                    <span className="truncate text-sm font-medium text-foreground">{p.name}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{p.job_role}</p>
                  <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      <span className="font-medium text-foreground">{p.candidate_count}</span> candidates
                    </span>
                    <span>{new Date(p.updated_at).toLocaleDateString()}</span>
                  </div>
                </Card>
              </Link>
            </StaggerItem>
          ))}
        </StaggerGroup>
      )}

      {projects && projects.length === 0 && !showCreate && (
        <p className="text-sm text-muted-foreground">
          No recruitment projects yet -- create one to start ranking candidates for a role.
        </p>
      )}
    </main>
  );
}
