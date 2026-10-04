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
