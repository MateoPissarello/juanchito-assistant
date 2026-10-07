import pytest
from juanchito_assitant.agents.cv_writer import (
    TailoredExperience,
    TailoredInitiative,
    TailoredProject,
    TailoredResumeContent,
)
from juanchito_assitant.agents.guardrails import FactualGuardrail
from juanchito_assitant.agents.matcher import MatchedContext, PersonalProjectMatch, WorkProjectMatch
from juanchito_assitant.models.job import JobRequirements
from juanchito_assitant.models.profile import PersonalInfo, SkillCategory


@pytest.fixture
def sample_context():
    job = JobRequirements(
        job_title="Senior Backend Engineer",
        role_summary="Develop scalable backend systems.",
    )
    personal = PersonalInfo(full_name="Mateo Pissarello", email="mateo@example.com")
    skills = [
        SkillCategory(category="Languages", skills=["Python", "Java", "TypeScript"]),
        SkillCategory(category="Backend", skills=["FastAPI", "Django", "PostgreSQL", "Redis"]),
        SkillCategory(category="Cloud", skills=["AWS", "Docker", "Kubernetes"]),
    ]
    work_matches = [
        WorkProjectMatch(
            company="Blend360 Colombia",
            role="Trainee",
            dates="Nov. 2024 – Jan. 2026",
            location="Bogotá",
            project_name="AIForms",
            bullets=["Built dynamic forms with Python."],
            technologies=["Python", "AWS", "FastAPI"],
        ),
        WorkProjectMatch(
            company="Blend360 Colombia",
            role="Trainee",
            dates="Nov. 2024 – Jan. 2026",
            location="Bogotá",
            project_name="Zammad on Kubernetes",
            bullets=["Migrated ECS to EKS."],
            technologies=["AWS", "Kubernetes", "EKS"],
        ),
    ]
    github_matches = [
        PersonalProjectMatch(
            name="goofish-scraping",
            repo_url="https://github.com/MateoPissarello/goofish-scraping",
            technologies=["Python", "Playwright"],
            year="2024",
            bullets=["Built scraping engine."],
        ),
        PersonalProjectMatch(
            name="CanvaToPdf",
            repo_url="https://github.com/MateoPissarello/CanvaToPdf",
            technologies=["Python", "PDF"],
            year="2024",
            bullets=["CLI tool for presentations."],
        ),
    ]

    return MatchedContext(
        target_job=job,
        personal_info=personal,
        work_matches=work_matches,
        github_matches=github_matches,
        skills=skills,
    )


def test_guardrail_purges_hallucinated_project(sample_context):
    content = TailoredResumeContent(
        headline="Senior Backend Engineer",
        profile_summary="Experienced backend engineer.",
        experiences=[
            TailoredExperience(
                company="Blend360 Colombia",
                role="Trainee",
                dates="Nov. 2024 – Jan. 2026",
                location="Bogotá",
                initiatives=[
                    TailoredInitiative(name="AIForms", bullets=["Built AIForms."])
                ],
            )
        ],
        projects=[
            # Proyecto REAL
            TailoredProject(
                name="CanvaToPdf",
                repo_url="https://github.com/fake/url",
                technologies=["Python", "PDF"],
                year="2024",
                bullets=["Exported presentations."],
            ),
            # Proyecto ALUCINADO (como el que ocurrió con Snowflake)
            TailoredProject(
                name="Snowflake Data Pipeline",
                repo_url=None,
                technologies=["Python", "Snowflake", "Azure Functions"],
                year="2024",
                bullets=["Built 1M record pipeline into Snowflake."],
            ),
        ],
        prioritized_skills={
            "Backend": ["Python", "FastAPI", "REST APIs"],
            "Cloud & Data": ["AWS", "Snowflake", "Azure Functions"],  # Snowflake y Azure son inventadas
        },
    )

    sanitized, alerts = FactualGuardrail.apply(content, sample_context)

    # 1. El proyecto alucinado debe haber sido eliminado
    assert len(sanitized.projects) == 1
    assert sanitized.projects[0].name == "CanvaToPdf"
    assert any("Snowflake Data Pipeline" in a for a in alerts)

    # 2. Las habilidades inventadas deben haber sido purgadas
    cloud_skills = sanitized.prioritized_skills.get("Cloud & Data", [])
    assert "AWS" in cloud_skills
    assert "Snowflake" not in cloud_skills
    assert "Azure Functions" not in cloud_skills

    # 3. Conceptos válidos como 'REST APIs' y 'Python' deben preservarse
    backend_skills = sanitized.prioritized_skills.get("Backend", [])
    assert "Python" in backend_skills
    assert "FastAPI" in backend_skills
    assert "REST APIs" in backend_skills


def test_guardrail_purges_hallucinated_company(sample_context):
    content = TailoredResumeContent(
        headline="Senior Backend Engineer",
        profile_summary="Backend summary.",
        experiences=[
            TailoredExperience(
                company="Google Inc.",  # Empresa ficticia nunca trabajada
                role="Staff Engineer",
                dates="2023 - 2024",
                location="Mountain View",
                initiatives=[
                    TailoredInitiative(name="Search Engine", bullets=["Built search."])
                ],
            ),
            TailoredExperience(
                company="Blend360 Colombia",
                role="Trainee",
                dates="Nov. 2024 – Jan. 2026",
                location="Bogotá",
                initiatives=[
                    TailoredInitiative(name="AIForms", bullets=["Built AIForms."])
                ],
            ),
        ],
        projects=[],
        prioritized_skills={"Backend": ["Python"]},
    )

    sanitized, alerts = FactualGuardrail.apply(content, sample_context)

    # La empresa falsa debe ser purgada
    assert len(sanitized.experiences) == 1
    assert sanitized.experiences[0].company == "Blend360 Colombia"
    assert any("Google Inc." in a for a in alerts)
