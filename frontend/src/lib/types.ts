export interface EligibilityResult {
  eligible: boolean;
  reasons: string[];
}

export interface DegreeInfo {
  all_degrees: string[];
  highest: string | null;
}

export interface RequirementVerdict {
  requirement: string;
  weight: number;
  satisfied: boolean;
  confidence: number;
  justification: string;
  evidence: string[];
  suggested_certification: string | null;
}

export interface JdRequirement {
  requirement: string;
  weight: number;
}

export interface ResumeSection {
  heading: string;
  lines: string[];
}

export interface OptimizedResume {
  full_name: string | null;
  contact_line: string | null;
  sections: ResumeSection[];
}

export interface JobSeekerPartial {
  resume_experience_years?: number;
  jd_experience_years?: number;
  resume_degree?: DegreeInfo;
  jd_degree?: DegreeInfo;
  eligibility?: EligibilityResult;
  jd_requirements?: JdRequirement[];
  cover_letter?: string;
  optimized_resume?: OptimizedResume;
}

export interface JobSeekerAnalysisResponse {
  eligibility: EligibilityResult;
  resume_degree: DegreeInfo;
  jd_degree: DegreeInfo;
  resume_experience_years: number;
  jd_experience_years: number;
  overall_fit_score: number;
  skill_based_ats_score: number;
  requirement_verdicts: RequirementVerdict[];
  matched_requirements: string[];
  missing_requirements: string[];
  cover_letter: string | null;
  optimized_resume: OptimizedResume | null;
}

export interface CandidateResult {
  filename: string;
  eligible: boolean;
  reasons: string[];
  experience_years: number;
  candidate_name: string | null;
  candidate_email: string | null;
  candidate_phone: string | null;
  overall_fit_score: number;
  skill_based_ats_score: number;
  matched_requirements: string[];
  missing_requirements: string[];
  requirement_verdicts: RequirementVerdict[];
  provisional_score: number;
  skill_match_score: number;
  shortlisted: boolean;
  round_reached: number; // 0=ineligible, 1=cut after round 1, 2=cut after round 2, 3=fully reviewed
}

export interface RecruiterAnalysisResponse {
  job_role: string;
  total_candidates: number;
  ranked_candidates: CandidateResult[];
}

export interface ResumeLibraryItem {
  id: string;
  filename: string;
  created_at: string;
}

export interface ReportSummary {
  id: string;
  resume_filename: string;
  job_role: string;
  overall_fit_score: number;
  skill_based_ats_score: number;
  created_at: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  job_role: string;
  num_vacancies: number | null;
  candidate_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail {
  id: string;
  name: string;
  job_role: string;
  job_desc_text: string;
  num_vacancies: number | null;
  candidates: CandidateResult[];
}

export type StepState = "pending" | "running" | "done";
export type JobState = "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "stopped";

export interface StageStatus {
  key: string;
  label: string;
  state: StepState;
}

export type CandidatePhase =
  | "pending"
  | "round1"
  | "round1_cut"
  | "round2"
  | "round2_cut"
  | "round3"
  | "done";

export interface CandidateStatus {
  filename: string;
  state: StepState;
  score: number | null;
  phase: CandidatePhase;
}

export interface RoundCandidateSummary {
  filename: string;
  eligible: boolean;
  reasons: string[];
  score: number;
  advancing: boolean;
}

export interface RoundSummary {
  round: number;
  label: string;
  candidates: RoundCandidateSummary[];
  advancing_count: number;
}

export interface JobStatusResponse {
  job_id: string;
  kind: "job_seeker" | "recruiter";
  state: JobState;
  stages: StageStatus[];
  candidates: CandidateStatus[];
  partial: JobSeekerPartial;
  verdicts: RequirementVerdict[];
  current_activity: string | null;
  pending_approval: RoundSummary | null;
  result: JobSeekerAnalysisResponse | RecruiterAnalysisResponse | null;
  error: string | null;
}
