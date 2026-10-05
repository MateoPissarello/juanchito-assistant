from pydantic import BaseModel, Field
from typing import Any


class PersonalInfoUpdate(BaseModel):
    full_name: str
    headline: str
    location: str = "Bogotá, Colombia"
    timezone: str = "GMT-05"
    email: str = "@EMAIL"
    phone: str = "@PHONE"
    linkedin: str = "mateo-pissarello"
    github: str = "MateoPissarello"
    profile_summary: str = ""
    extra_variables: dict[str, str] = Field(default_factory=dict)


class WorkProjectCreate(BaseModel):
    work_experience_id: int
    name: str
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    priority_weight: int = 1


class WorkProjectUpdate(BaseModel):
    name: str | None = None
    bullets: list[str] | None = None
    technologies: list[str] | None = None
    priority_weight: int | None = None


class WorkExperienceCreate(BaseModel):
    company: str
    role: str
    location: str = "Bogotá, Colombia"
    start_date: str
    end_date: str = "Present"
    is_current: bool = False
    order_index: int = 0


class WorkExperienceUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool | None = None
    order_index: int | None = None


class TrackedRepoCreate(BaseModel):
    name: str
    branch: str | None = None
    is_active: bool = True
    priority: int = 1
    category: str | None = None
    notes: str | None = None


class TrackedRepoUpdate(BaseModel):
    branch: str | None = None
    is_active: bool | None = None
    priority: int | None = None
    category: str | None = None
    notes: str | None = None


class SkillCategoryCreate(BaseModel):
    category: str
    skills: list[str] = Field(default_factory=list)


class SkillCategoryUpdate(BaseModel):
    category: str | None = None
    skills: list[str] | None = None


class CertificationCreate(BaseModel):
    issuer: str
    title: str
    issue_date: str


class CertificationUpdate(BaseModel):
    issuer: str | None = None
    title: str | None = None
    issue_date: str | None = None
