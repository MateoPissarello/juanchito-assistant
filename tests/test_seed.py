import pytest
from pathlib import Path
from sqlmodel import Session, create_engine, select, SQLModel
from juanchito_assitant.config import PROJECT_ROOT
from juanchito_assitant.ingest.markdown_parser import parse_resume_markdown, seed_database_from_profile
from juanchito_assitant.models.profile import (
    PersonalInfo,
    WorkExperience,
    WorkProject,
    Certification,
    Education,
    SkillCategory,
    AdditionalAchievement,
)

def test_parse_and_seed_real_resume():
    resume_path = PROJECT_ROOT / "data/examples/Backend Engineer/resume.md"
    assert resume_path.exists(), "El archivo de ejemplo resume.md debe existir"

    content = resume_path.read_text(encoding="utf-8")
    profile = parse_resume_markdown(content)

    assert profile.personal.full_name == "Mateo Pissarello"
    assert "Backend Engineer" in profile.personal.headline
    assert len(profile.experiences) == 2
    assert len(profile.certifications) == 8
    assert len(profile.skills) >= 6
    assert len(profile.additional_achievements) == 1

    # Verificar iniciativas de Blend360
    blend = next(e for e in profile.experiences if "Blend360" in e.company)
    assert len(blend.projects) == 5
    project_names = [p.name for p in blend.projects]
    assert "AICodeFixer" in project_names
    assert "Zammad on Kubernetes (EKS)" in project_names

    # Test de inserción en SQLite en memoria
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        seed_database_from_profile(profile, session)

        # Consultas de verificación en DB
        p_db = session.exec(select(PersonalInfo)).first()
        assert p_db is not None
        assert p_db.full_name == "Mateo Pissarello"

        exp_db = session.exec(select(WorkExperience)).all()
        assert len(exp_db) == 2

        certs_db = session.exec(select(Certification)).all()
        assert len(certs_db) == 8

        ach_db = session.exec(select(AdditionalAchievement)).first()
        assert ach_db is not None
        assert "SPICY" in ach_db.description_bullets[0]
