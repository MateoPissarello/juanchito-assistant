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
