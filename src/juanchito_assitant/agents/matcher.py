import re
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from juanchito_assitant.models.job import JobRequirements
from juanchito_assitant.models.profile import (
    AdditionalAchievement,
    Certification,
    Education,
    PersonalInfo,
    PersonalProject,
    SkillCategory,
    WorkExperience,
    WorkProject,
)


def _normalize(term: str) -> str:
    return re.sub(r"[^\w\s]", "", term.lower()).strip()


def _score_text_and_techs(
    techs: list[str],
    text_corpus: str,
    must_haves: list[str],
    nice_to_haves: list[str],
    ats_keywords: list[str],
) -> tuple[float, list[str]]:
    """Calcula el puntaje de afinidad y retorna las tecnologías que hicieron match."""
    score = 0.0
    matched_skills: set[str] = set()

    corpus_lower = text_corpus.lower()
    techs_lower = {t.lower(): t for t in techs}

    for must in must_haves:
        m_norm = must.lower()
        if any(m_norm in t_low for t_low in techs_lower) or m_norm in corpus_lower:
            score += 3.0
            matched_skills.add(must)

    for nice in nice_to_haves:
        n_norm = nice.lower()
        if any(n_norm in t_low for t_low in techs_lower) or n_norm in corpus_lower:
            score += 1.5
            matched_skills.add(nice)

    for kw in ats_keywords:
        k_norm = kw.lower()
        if any(k_norm in t_low for t_low in techs_lower) or k_norm in corpus_lower:
            score += 1.0
            matched_skills.add(kw)

    return score, list(matched_skills)


class WorkProjectMatch(BaseModel):
    company: str
    role: str
    dates: str
    location: str
    project_name: str
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    match_score: float = 0.0
    matching_skills: list[str] = Field(default_factory=list)


class PersonalProjectMatch(BaseModel):
    name: str
    repo_url: str | None = None
    description: str | None = None
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    match_score: float = 0.0
    matching_skills: list[str] = Field(default_factory=list)


class MatchedContext(BaseModel):
    personal_info: PersonalInfo
    work_matches: list[WorkProjectMatch] = Field(default_factory=list)
    github_matches: list[PersonalProjectMatch] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    skills: list[SkillCategory] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    achievements: list[AdditionalAchievement] = Field(default_factory=list)
    target_job: JobRequirements


class MatcherAgent:
    """Agente para cruzar los requisitos del empleo contra los activos de profile.db."""

    def __init__(self, session: Session):
        self.session = session

    def match(
        self,
        job: JobRequirements,
        max_work_projects: int = 4,
        max_github_projects: int = 2,
    ) -> MatchedContext:
        """Puntúa y selecciona los activos más relevantes para la vacante."""
        # 1. Información Personal
        personal = self.session.exec(select(PersonalInfo)).first() or PersonalInfo()

        # 2. Experiencia Laboral e Iniciativas
        experiences = self.session.exec(select(WorkExperience).order_by(WorkExperience.order_index)).all()
        scored_work_projects: list[WorkProjectMatch] = []

        for exp in experiences:
            date_str = f"{exp.start_date} – {exp.end_date}"
            for proj in exp.projects:
                text_corpus = f"{proj.name} {' '.join(proj.bullets)} {' '.join(proj.technologies)}"
                score, matched_skills = _score_text_and_techs(
                    techs=proj.technologies,
                    text_corpus=text_corpus,
                    must_haves=job.must_have_skills,
                    nice_to_haves=job.nice_to_have_skills,
                    ats_keywords=job.ats_keywords,
                )
                scored_work_projects.append(
                    WorkProjectMatch(
                        company=exp.company,
                        role=exp.role,
                        dates=date_str,
                        location=exp.location,
                        project_name=proj.name,
                        bullets=proj.bullets,
                        technologies=proj.technologies,
                        match_score=score,
                        matching_skills=matched_skills,
                    )
                )

        # Ordenar proyectos por score descendente y seleccionar los mejores
        scored_work_projects.sort(key=lambda x: x.match_score, reverse=True)
        selected_work = scored_work_projects[:max_work_projects]

        # 3. Proyectos Personales / Repositorios GitHub
        github_repos = self.session.exec(select(PersonalProject)).all()
        scored_repos: list[PersonalProjectMatch] = []

        for repo in github_repos:
            text_corpus = f"{repo.name} {repo.description or ''} {' '.join(repo.bullets)} {' '.join(repo.technologies)}"
            score, matched_skills = _score_text_and_techs(
                techs=repo.technologies,
                text_corpus=text_corpus,
                must_haves=job.must_have_skills,
                nice_to_haves=job.nice_to_have_skills,
                ats_keywords=job.ats_keywords,
            )
            scored_repos.append(
                PersonalProjectMatch(
                    name=repo.name,
                    repo_url=repo.repo_url or f"https://github.com/{personal.github}/{repo.name}",
                    description=repo.description,
                    bullets=repo.bullets,
                    technologies=repo.technologies,
                    match_score=score,
                    matching_skills=matched_skills,
                )
            )

        scored_repos.sort(key=lambda x: x.match_score, reverse=True)
        selected_github = scored_repos[:max_github_projects]

        # 4. Certificaciones
        certs = self.session.exec(select(Certification)).all()
        # Priorizar certificaciones relevantes para el cloud o stack solicitado
        def cert_relevance(c: Certification) -> int:
            t = f"{c.issuer} {c.title}".lower()
            return sum(2 for m in job.must_have_skills if m.lower() in t) + sum(1 for n in job.nice_to_have_skills if n.lower() in t)

        certs.sort(key=cert_relevance, reverse=True)

        # 5. Habilidades (Ordenar categorías según relevancia para el rol)
        categories = self.session.exec(select(SkillCategory)).all()
        def category_score(cat: SkillCategory) -> int:
            skills_str = " ".join(cat.skills).lower()
            return sum(3 for m in job.must_have_skills if m.lower() in skills_str) + sum(1 for n in job.nice_to_have_skills if n.lower() in skills_str)

        categories.sort(key=category_score, reverse=True)

        # 6. Educación y Logros Adicionales
        education = self.session.exec(select(Education)).all()
        achievements = self.session.exec(select(AdditionalAchievement)).all()

        return MatchedContext(
            personal_info=personal,
            work_matches=selected_work,
            github_matches=selected_github,
            certifications=certs,
            skills=categories,
            education=education,
            achievements=achievements,
            target_job=job,
        )
