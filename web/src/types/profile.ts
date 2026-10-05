export interface PersonalInfo {
  id?: number;
  full_name: string;
  headline: string;
  location: string;
  timezone: string;
  email: string;
  phone: string;
  linkedin: string;
  github: string;
  profile_summary: string;
  extra_variables?: Record<string, string>;
}

export interface WorkProject {
  id?: number;
  work_experience_id: number;
  name: string;
  bullets: string[];
  technologies: string[];
  priority_weight: number;
}

export interface WorkExperience {
  id?: number;
  company: string;
  role: string;
  location: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  order_index: number;
  projects: WorkProject[];
}

export interface TrackedRepo {
  id?: number;
  name: string;
  branch: string | null;
  is_active: boolean;
  priority: number;
  category: string | null;
  notes: string | null;
}

export interface PersonalProject {
  id?: number;
  name: string;
  repo_url: string | null;
  branch: string;
  description: string | null;
  bullets: string[];
  technologies: string[];
  has_readme: boolean;
  suggested_readme: string | null;
  last_pushed_at: string | null;
}

export interface SkillCategory {
  id?: number;
  category: string;
  skills: string[];
}

export interface Certification {
  id?: number;
  issuer: string;
  title: string;
  issue_date: string;
}

export interface Education {
  id?: number;
  institution: string;
  degree: string;
  date_range: string;
  location: string;
}

export interface FullProfileData {
  personal: PersonalInfo;
  experiences: WorkExperience[];
  tracked_repos: TrackedRepo[];
  personal_projects: PersonalProject[];
  skills: SkillCategory[];
  certifications: Certification[];
  education: Education[];
  additional_achievements: any[];
}

export interface ScoreBreakdown {
  ats_keyword_match: number;
  role_relevance: number;
  quantifiable_impact: number;
  factual_integrity: number;
  format_and_length: number;
}

export interface EvaluationResult {
  total_score: number;
  decision: string;
  meets_threshold: boolean;
  breakdown: ScoreBreakdown;
  strengths: string[];
  critical_weaknesses: string[];
  actionable_improvements: string[];
}

export interface JobRequirements {
  job_title: string;
  company_name: string | null;
  seniority_level: string | null;
  must_have_skills: string[];
  nice_to_have_skills: string[];
  core_responsibilities: string[];
  ats_keywords: string[];
  role_summary: string;
}

export interface TailoringReport {
  job: JobRequirements;
  final_markdown: string;
  final_evaluation: EvaluationResult;
  iterations: any[];
  output_file_path: string;
}

export interface StreamProgressEvent {
  type: 'analyzing' | 'matching' | 'writing' | 'evaluating' | 'completed' | 'error';
  message: string;
  step?: number;
  total_steps?: number;
  iteration?: number;
  job_title?: string;
  company?: string;
  keywords?: string[];
  report?: TailoringReport;
}

export interface ResumeHistoryItem {
  filename: string;
  company: string;
  role: string;
  created_at: string;
  timestamp_raw: string;
  language: 'en' | 'es';
  headline?: string;
  size_bytes: number;
  word_count: number;
  ats_score?: number | null;
  ats_decision?: string | null;
}

export interface ResumeHistoryDetail extends ResumeHistoryItem {
  markdown: string;
  evaluation?: EvaluationResult | null;
}


