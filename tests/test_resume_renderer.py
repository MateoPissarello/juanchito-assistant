from sqlmodel import Session, SQLModel, create_engine

from juanchito_assitant.agents.matcher import MatcherAgent
from juanchito_assitant.models.job import JobRequirements
from juanchito_assitant.models.profile import (
    Certification,
    Education,
    PersonalInfo,
    SkillCategory,
    WorkExperience,
    WorkProject,
)
from juanchito_assitant.rendering.resume_renderer import ResumeRenderer


def test_resume_renderer_html_structure():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    # Seed
    p = PersonalInfo(full_name="Mateo Pissarello", email="test@example.com")
    session.add(p)
    w = WorkExperience(company="Blend360 Colombia", role="Backend Engineer", location="Bogotá", start_date="Nov. 2024", end_date="Jan. 2026")
    session.add(w)
    session.flush()
    wp = WorkProject(work_experience_id=w.id, name="AICodeFixer", bullets=["Bullet 1"], technologies=["Python"])
    session.add(wp)
    c = Certification(issuer="Amazon Web Services (AWS)", title="AWS Solutions Architect", issue_date="Apr. 2025")
    session.add(c)
    e = Education(institution="Universidad Sergio Arboleda", degree="B.Sc. Computer Science", date_range="2022-Present", location="Bogotá")
    session.add(e)
    session.commit()

    matcher = MatcherAgent(session)
    job = JobRequirements(job_title="Backend Developer", must_have_skills=["Python"], role_summary="Dev role")
    ctx = matcher.match(job)

    rendered = ResumeRenderer.render(
        headline="Backend Engineer | Cloud Specialist",
        profile_summary="Passionate engineer building distributed systems.",
        experiences=[
            {
                "company": "Blend360 Colombia",
                "role": "Backend Engineer",
                "dates": "Nov. 2024 – Jan. 2026",
                "location": "Bogotá, Colombia",
                "initiatives": [
                    {
                        "name": "AICodeFixer",
                        "bullets": ["Optimized backend latency by **40%** using **FastAPI**."],
                    }
                ],
            }
        ],
        skills={"Backend": ["FastAPI", "Python"], "Cloud": ["AWS", "Docker"]},
        matched_ctx=ctx,
    )

    # 1. Variables de cabecera
    assert "@NAME=Mateo Pissarello||Hidden Name" in rendered
    assert "@EMAIL=" in rendered
    assert "@TZ=" in rendered

    # 2. Clases HTML
    assert '<div class="headline">' in rendered
    assert '<div class="section headerInfo">' in rendered
    assert "</div>" in rendered

    # 3. Separadores flexbox
    assert '<span class="spacer"></span><span class="normal"> Nov. 2024 – Jan. 2026 </span>' in rendered
    assert '#### Blend360 Colombia <span class="spacer"></span> Bogotá, Colombia' in rendered

    # 4. Formato de iniciativas
    assert "- **AICodeFixer**" in rendered
    assert "    - Optimized backend latency by **40%** using **FastAPI**." in rendered

    # 5. Certificaciones y Educación
    assert "### Amazon Web Services (AWS)" in rendered
    assert '#### AWS Solutions Architect <span class="spacer"></span><span class="normal">Apr. 2025</span>' in rendered
    assert "### Universidad Sergio Arboleda" in rendered


def test_resume_renderer_spanish_headers():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    p = PersonalInfo(full_name="Mateo Pissarello")
    session.add(p)
    w = WorkExperience(company="Blend360", role="Backend Engineer", location="Bogotá", start_date="2024", end_date="Present")
    session.add(w)
    session.commit()

    matcher = MatcherAgent(session)
    job = JobRequirements(job_title="Backend Dev", must_have_skills=["Python"], role_summary="Dev")
    ctx = matcher.match(job)

    rendered = ResumeRenderer.render(
        headline="Ingeniero de Software",
        profile_summary="Especialista en sistemas distribuidos.",
        experiences=[{"company": "Blend360", "role": "Ingeniero", "dates": "2024 - Present", "location": "Remote", "initiatives": []}],
        skills={"Backend": ["Python"]},
        matched_ctx=ctx,
        language="es",
    )
    assert "## Perfil Profesional" in rendered
    assert "## Experiencia Laboral" in rendered
    assert "## Habilidades" in rendered
    assert "Presente" in rendered
    assert "Remoto" in rendered


def test_resume_renderer_with_projects_estilo_1():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    p = PersonalInfo(full_name="Mateo Pissarello")
    session.add(p)
    session.commit()

    matcher = MatcherAgent(session)
    job = JobRequirements(job_title="Backend Dev", must_have_skills=["FastAPI"], role_summary="Dev")
    ctx = matcher.match(job)

    custom_projects = [
        {
            "name": "Cine Colombia API",
            "repo_url": "https://github.com/MateoPissarello/cine_colombia",
            "technologies": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "year": "2024",
            "bullets": [
                "Diseñé e implementé una arquitectura backend con **FastAPI** y **PostgreSQL**.",
                "Configuré pipeline de CI/CD y despliegue contenerizado con **Docker**.",
            ],
        }
    ]

    rendered = ResumeRenderer.render(
        headline="Backend Engineer",
        profile_summary="Passionate engineer.",
        experiences=[],
        skills={"Backend": ["FastAPI"]},
        matched_ctx=ctx,
        language="en",
        projects=custom_projects,
    )

    # Verifica encabezado de proyectos en inglés
    assert "## Projects" in rendered
    # Verifica Estilo 1 para enlace de GitHub
    assert '### Cine Colombia API <span class="spacer"></span><span class="normal"> [github.com/MateoPissarello/cine_colombia](https://github.com/MateoPissarello/cine_colombia) </span>' in rendered
    # Verifica línea de tecnologías y año
    assert '#### Python, FastAPI, PostgreSQL, Docker <span class="spacer"></span> 2024' in rendered
    # Verifica viñetas de proyecto
    assert "- Diseñé e implementé una arquitectura backend con **FastAPI** y **PostgreSQL**." in rendered
    assert "- Configuré pipeline de CI/CD y despliegue contenerizado con **Docker**." in rendered


def test_resume_renderer_spanish_projects():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    p = PersonalInfo(full_name="Mateo Pissarello")
    session.add(p)
    session.commit()

    matcher = MatcherAgent(session)
    job = JobRequirements(job_title="Backend Dev", must_have_skills=["Python"], role_summary="Dev")
    ctx = matcher.match(job)

    custom_projects = [
        {
            "name": "Scraper Pro",
            "repo_url": "https://github.com/MateoPissarello/scraper",
            "technologies": ["Python", "Playwright"],
            "year": "2024",
            "bullets": ["Automatización de extracción de datos."],
        }
    ]

    rendered = ResumeRenderer.render(
        headline="Desarrollador Backend",
        profile_summary="Resumen.",
        experiences=[],
        skills={"Backend": ["Python"]},
        matched_ctx=ctx,
        language="es",
        projects=custom_projects,
    )

    # En español debe usar '## Proyectos'
    assert "## Proyectos" in rendered
    assert "### Scraper Pro" in rendered
    assert "- Automatización de extracción de datos." in rendered


def test_resume_renderer_projects_fallback_from_context():
    from juanchito_assitant.models.profile import PersonalProject

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    p = PersonalInfo(full_name="Mateo Pissarello")
    session.add(p)
    repo = PersonalProject(
        name="goofish-scraping",
        repo_url="https://github.com/MateoPissarello/goofish-scraping",
        technologies=["Python", "FastAPI"],
        bullets=["Extracción distribuida de datos."],
    )
    session.add(repo)
    session.commit()

    matcher = MatcherAgent(session)
    job = JobRequirements(job_title="Python Dev", must_have_skills=["Python"], role_summary="Dev")
    ctx = matcher.match(job)

    # Si projects es None, toma github_matches del contexto automáticamente
    rendered = ResumeRenderer.render(
        headline="Software Engineer",
        profile_summary="Summary.",
        experiences=[],
        skills={},
        matched_ctx=ctx,
        language="en",
        projects=None,
    )

    assert "## Projects" in rendered
    assert "### goofish-scraping" in rendered
    assert "- Extracción distribuida de datos." in rendered


