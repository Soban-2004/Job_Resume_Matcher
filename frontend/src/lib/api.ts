import { createClient } from "@/lib/supabase/client";
import type {
  JobSeekerAnalysisResponse,
  JobStatusResponse,
  OptimizedResume,
  ProjectDetail,
  ProjectSummary,
  ReportSummary,
  ResumeLibraryItem,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

async function authHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session ? { Authorization: `Bearer ${session.access_token}` } : {};
}

export async function createJobSeekerJob(
  resume: File,
  jobDescription: File,
  jobRole: string
): Promise<string> {
  const form = new FormData();
  form.append("resume", resume);
  form.append("job_description", jobDescription);
  form.append("job_role", jobRole);

  const res = await fetch(`${API_BASE_URL}/api/job-seeker/jobs`, {
    method: "POST",
    headers: await authHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  const data = await res.json();
  return data.job_id as string;
}

export async function getJobSeekerJob(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/job-seeker/jobs/${jobId}`);
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function stopJobSeekerJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/job-seeker/jobs/${jobId}/stop`, { method: "POST" });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
}

export async function listResumes(): Promise<ResumeLibraryItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/job-seeker/resumes`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function listReports(): Promise<ReportSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/job-seeker/reports`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function getReport(reportId: string): Promise<JobSeekerAnalysisResponse> {
  const res = await fetch(`${API_BASE_URL}/api/job-seeker/reports/${reportId}`, {
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function downloadOptimizedResumePdf(resume: OptimizedResume): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/job-seeker/optimized-resume/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(resume),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${(resume.full_name ?? "resume").replace(/\s+/g, "_")}_optimized.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function createProject(
  name: string,
  jobRole: string,
  jobDescription: File,
  numVacancies?: number
): Promise<{ id: string; name: string }> {
  const form = new FormData();
  form.append("name", name);
  form.append("job_role", jobRole);
  form.append("job_description", jobDescription);
  if (numVacancies != null) {
    form.append("num_vacancies", String(numVacancies));
  }

  const res = await fetch(`${API_BASE_URL}/api/recruiter/projects`, {
    method: "POST",
    headers: await authHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/recruiter/projects`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  const res = await fetch(`${API_BASE_URL}/api/recruiter/projects/${projectId}`, {
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function createProjectBatch(projectId: string, resumes: File[]): Promise<string> {
  const form = new FormData();
  for (const resume of resumes) {
    form.append("resumes", resume);
  }

  const res = await fetch(`${API_BASE_URL}/api/recruiter/projects/${projectId}/jobs`, {
    method: "POST",
    headers: await authHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  const data = await res.json();
  return data.job_id as string;
}

export async function getRecruiterJob(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/recruiter/jobs/${jobId}`);
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function approveNextRound(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/recruiter/jobs/${jobId}/approve`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
}

export async function stopRecruiterJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/recruiter/jobs/${jobId}/stop`, { method: "POST" });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
}

export async function sendCandidateEmail(toEmail: string, subject: string, body: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/recruiter/send-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ to_email: toEmail, subject, body }),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
}
