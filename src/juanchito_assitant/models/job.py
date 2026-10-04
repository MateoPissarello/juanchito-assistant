from pydantic import BaseModel, Field


class JobRequirements(BaseModel):
    job_title: str
    company_name: str | None = None
    seniority_level: str | None = "Mid-Senior"
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    core_responsibilities: list[str] = Field(default_factory=list)
    ats_keywords: list[str] = Field(default_factory=list)
    role_summary: str
