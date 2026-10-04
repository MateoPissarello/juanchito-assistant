import pytest
from pathlib import Path
from sqlmodel import Session, create_engine, select, SQLModel
from juanchito_assitant.models.profile import (
    PersonalInfo,
    WorkExperience,
    WorkProject,
    PersonalProject,
    Certification,
    Education,
    SkillCategory,
    AdditionalAchievement,
)

@pytest.fixture
def session():
    """Crea una base de datos SQLite en memoria para pruebas aisladas."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s

def test_create_personal_info(session: Session):
    info = PersonalInfo(
        full_name="Mateo Pissarello",
        email="mateopissa@gmail.com",
        headline="Backend Engineer | AWS",
    )
    session.add(info)
    session.commit()

    retrieved = session.exec(select(PersonalInfo)).first()
    assert retrieved is not None
    assert retrieved.full_name == "Mateo Pissarello"
    assert retrieved.headline == "Backend Engineer | AWS"

def test_work_experience_with_projects(session: Session):
    # 1. Crear experiencia laboral
    exp = WorkExperience(
        company="Blend360 Colombia",
        role="Trainee",
        location="Bogotá, Colombia (On-site)",
        start_date="Nov. 2024",
        end_date="Jan. 2026",
    )
    session.add(exp)
    session.commit()
    session.refresh(exp)

    # 2. Agregar iniciativas técnicas a ese cargo
    proj1 = WorkProject(
        work_experience_id=exp.id,
        name="AICodeFixer",
        bullets=[
            "Created AICodeFixer integrated with SonarQube and GitHub.",
            "Developed FastAPI workflow reducing resolution time by 50%."
        ],
        technologies=["FastAPI", "AWS Lambda", "DynamoDB", "ClaudeCode"]
    )
    proj2 = WorkProject(
        work_experience_id=exp.id,
        name="AIForms",
        bullets=["Developed AIForms deployed on AWS Fargate."],
        technologies=["Python", "Docassemble", "AWS CDK"]
    )
    session.add_all([proj1, proj2])
    session.commit()

    # 3. Consultar y verificar la relación 1 a N
    exp_db = session.exec(select(WorkExperience).where(WorkExperience.company == "Blend360 Colombia")).first()
    assert exp_db is not None
    assert len(exp_db.projects) == 2
    project_names = [p.name for p in exp_db.projects]
    assert "AICodeFixer" in project_names
    assert "AIForms" in project_names

    # Verificar que las viñetas y tecnologías se recuperan como listas
    aicodefixer = next(p for p in exp_db.projects if p.name == "AICodeFixer")
    assert len(aicodefixer.bullets) == 2
    assert "FastAPI" in aicodefixer.technologies

def test_additional_achievement(session: Session):
    achievement = AdditionalAchievement(
        category="Programming Contest",
        title="Programming Contest 2024-2",
        institution="Universidad Sergio Arboleda",
        description_bullets=["My team SPICY achieved third place among 25 teams."],
        links=[{"label": "MARATON", "url": "https://example.com/noticia"}]
    )
    session.add(achievement)
    session.commit()

    retrieved = session.exec(select(AdditionalAchievement)).first()
    assert retrieved is not None
    assert retrieved.title == "Programming Contest 2024-2"
    assert "SPICY" in retrieved.description_bullets[0]
