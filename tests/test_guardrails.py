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


def test_classify_job_skills_separates_owned_vs_unowned(sample_context):
    sample_context.target_job.must_have_skills = ["Python", "FastAPI", "Snowflake", "Microsoft Azure"]
    sample_context.target_job.nice_to_have_skills = ["Docker", "Databricks"]

    owned, unowned = FactualGuardrail.classify_job_skills(sample_context.target_job, sample_context)
    owned_low = [s.lower() for s in owned]
    unowned_low = [s.lower() for s in unowned]

    assert "python" in owned_low
    assert "fastapi" in owned_low
    assert "docker" in owned_low
    assert "snowflake" in unowned_low
    assert "databricks" in unowned_low
    assert any("azure" in u for u in unowned_low)


def test_guardrail_blocks_hallucinated_tech_inside_bullets_and_project_techs(sample_context):
    sample_context.target_job.must_have_skills = ["Python", "FastAPI", "Snowflake"]

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
                    TailoredInitiative(
                        name="AIForms",
                        bullets=[
                            "Architected high-throughput data ingestion into **Snowflake** reducing latency by **40%**.",
                            "Developed scalable REST APIs with **Python** and **FastAPI** improving response times by **30%**.",
                        ],
                    )
                ],
            )
        ],
        projects=[
            TailoredProject(
                name="CanvaToPdf",
                repo_url="https://github.com/MateoPissarello/CanvaToPdf",
                technologies=["Python", "Snowflake", "Databricks"],
                year="2024",
                bullets=[
                    "Automated PDF generation using **Python** and **Azure Functions**.",
                ],
            )
        ],
        prioritized_skills={"Backend": ["Python", "FastAPI"]},
    )

    sanitized, alerts = FactualGuardrail.apply(content, sample_context)

    # 1. En AIForms, la viñeta con **Snowflake** debe haber sido reemplazada por la original de SQLite
    aiforms_bullets = sanitized.experiences[0].initiatives[0].bullets
    assert not any("snowflake" in b.lower() for b in aiforms_bullets)
    assert "Built dynamic forms with Python." in aiforms_bullets
    assert any("Python" in b and "FastAPI" in b for b in aiforms_bullets)

    # 2. En CanvaToPdf, Snowflake y Databricks deben ser purgados de technologies y Azure Functions de bullets
    proj = sanitized.projects[0]
    assert "Snowflake" not in proj.technologies
    assert "Databricks" not in proj.technologies
    assert "Python" in proj.technologies
    assert not any("azure" in b.lower() for b in proj.bullets)
    assert "CLI tool for presentations." in proj.bullets
    assert len(alerts) >= 3


def test_classify_job_skills_splits_slash_compound_skills_and_restores_omitted_initiatives(sample_context):
    sample_context.target_job.must_have_skills = ["Python/FastAPI", "Java/Spring", ".NET/C#", "Kubernetes"]

    owned, unowned = FactualGuardrail.classify_job_skills(sample_context.target_job, sample_context)
    owned_low = [s.lower() for s in owned]
    unowned_low = [s.lower() for s in unowned]

    # Python y FastAPI están en sample_context -> nunca deben caer en unowned como 'python/fastapi'
    assert "python" in owned_low
    assert "fastapi" in owned_low
    assert "kubernetes" in owned_low
    assert "python/fastapi" not in unowned_low
    assert ".net" in unowned_low or "c#" in unowned_low

    # Si el WriterAgent omite 'Zammad on Kubernetes' de Blend360 Colombia, el Guardrail debe restaurarla
    content = TailoredResumeContent(
        headline="Backend Engineer",
        profile_summary="Summary.",
        experiences=[
            TailoredExperience(
                company="Blend360 Colombia",
                role="Trainee",
                dates="Nov. 2024 – Jan. 2026",
                location="Bogotá",
                initiatives=[
                    TailoredInitiative(name="AIForms", bullets=["Built dynamic forms with Python."])
                ],
            )
        ],
        projects=[],
        prioritized_skills={"Backend": ["Python", "FastAPI"]},
    )
    sanitized, _ = FactualGuardrail.apply(content, sample_context)
    init_names = [i.name for i in sanitized.experiences[0].initiatives]
    assert "AIForms" in init_names
    assert "Zammad on Kubernetes" in init_names


def test_guardrail_sql_and_spanish_job_skills_not_blocked_in_spanish_cv(sample_context):
    sample_context.target_job.must_have_skills = [
        "Python",
        "APIs REST",
        "Microservicios",
        "SQL",
        "JSON",
        "Integraciones",
    ]

    owned, unowned = FactualGuardrail.classify_job_skills(sample_context.target_job, sample_context)
    unowned_low = [u.lower() for u in unowned]

    # El candidato tiene PostgreSQL y FastAPI en sample_context -> SQL, APIs REST, JSON e Integraciones NO deben ser unowned
    assert "sql" not in unowned_low
    assert "apis rest" not in unowned_low
    assert "json" not in unowned_low
    assert "integraciones" not in unowned_low

    content = TailoredResumeContent(
        headline="Ingeniero Backend",
        profile_summary="Especialista en APIs.",
        experiences=[],
        projects=[
            TailoredProject(
                name="CanvaToPdf",
                repo_url="https://github.com/MateoPissarello/CanvaToPdf",
                technologies=["Python", "PostgreSQL"],
                year="2025",
                bullets=[
                    "Optimicé las consultas **SQL** en **PostgreSQL** reduciendo la latencia en un **40%**."
                ],
            )
        ],
        prioritized_skills={"Backend": ["Python", "FastAPI"]},
    )

    sanitized, alerts = FactualGuardrail.apply(content, sample_context, language="es")
    assert len(alerts) == 0
    assert "Optimicé las consultas **SQL** en **PostgreSQL** reduciendo la latencia en un **40%**." in sanitized.projects[0].bullets

