from sqlmodel import Session, SQLModel, create_engine, select

from juanchito_assitant.ingest.linkedin_enricher import enrich_profile_from_linkedin
from juanchito_assitant.models.linkedin import (
    LinkedInCertificationItem,
    LinkedInExperienceItem,
    LinkedInProfileExtract,
)
from juanchito_assitant.models.profile import (
    Certification,
    SkillCategory,
    WorkExperience,
    WorkProject,
)


def get_test_session():
    test_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(test_engine)
    return Session(test_engine)


def test_enrich_profile_non_destructive():
    with get_test_session() as session:
        # 1. Sembrar estado previo en base de datos
        existing_exp = WorkExperience(
            role="Trainee",
            company="Blend360 Colombia",
            location="Bogotá",
            start_date="Nov. 2024",
            end_date="Jan. 2026",
        )
        session.add(existing_exp)
        session.flush()

        proj1 = WorkProject(
            work_experience_id=existing_exp.id,
            name="AICodeFixer",
            bullets=["Engineered automated code remediation pipeline."],
            technologies=["Python", "FastAPI"],
        )
        session.add(proj1)

        cert1 = Certification(
            issuer="Amazon Web Services (AWS)",
            title="AWS Certified Solutions Architect - Associate",
            issue_date="Apr. 2025",
        )
        session.add(cert1)

        skill_cat = SkillCategory(
            category="Languages",
            skills=["Python", "SQL"],
        )
        session.add(skill_cat)
        session.commit()

        # 2. Simular extracción de LinkedIn con:
        # - Blend (existente: no debe pisar AICodeFixer)
        # - Icebergdata (nueva empresa técnica: debe agregarse)
        # - Teleperformance (no técnica: debe omitirse por defecto)
        # - Nueva certificación: Cloud Practitioner
        # - Nueva habilidad: Docker (debe categorizarse)
        extract = LinkedInProfileExtract(
            full_name="Mateo Pissarello",
            headline="Backend Engineer",
            experiences=[
                LinkedInExperienceItem(
                    company="Blend",
                    role="Data Analyst Trainee",
                    start_date="Nov. 2024",
                    end_date="Jan. 2026",
                    is_technical=True,
                    bullets=["Worked on analytics."],
                    technologies=["Python"],
                ),
                LinkedInExperienceItem(
                    company="Icebergdata",
                    role="Junior Backend Engineer",
                    start_date="Jan. 2026",
                    end_date="Mar. 2026",
                    is_technical=True,
                    bullets=["Built web scraping pipelines."],
                    technologies=["Python", "Playwright"],
                ),
                LinkedInExperienceItem(
                    company="Teleperformance",
                    role="Customer Service Representative",
                    start_date="Jun. 2023",
                    end_date="Aug. 2023",
                    is_technical=False,
                    bullets=["Handled calls."],
                    technologies=[],
                ),
            ],
            certifications=[
                LinkedInCertificationItem(
                    issuer="Amazon Web Services (AWS)",
                    title="AWS Certified Solutions Architect - Associate",  # Ya existe
                    issue_date="Apr. 2025",
                ),
                LinkedInCertificationItem(
                    issuer="Amazon Web Services (AWS)",
                    title="AWS Certified Cloud Practitioner",  # Nueva
                    issue_date="Dec. 2024",
                ),
            ],
            skills=["Python", "Docker"],  # Python ya existe, Docker es nueva
        )

        # 3. Ejecutar enriquecimiento
        summary = enrich_profile_from_linkedin(session, extract, dry_run=False, include_non_technical=False)

        # 4. Validar resultados
        # Blend preservado
        assert any("Blend360 Colombia" in e for e in summary.existing_experiences)
        db_blend = session.exec(select(WorkExperience).where(WorkExperience.company == "Blend360 Colombia")).first()
        assert len(db_blend.projects) == 1
        assert db_blend.projects[0].name == "AICodeFixer"

        # Icebergdata agregado
        assert any("Icebergdata" in a for a in summary.added_experiences)
        db_iceberg = session.exec(select(WorkExperience).where(WorkExperience.company == "Icebergdata")).first()
        assert db_iceberg is not None
        assert db_iceberg.role == "Junior Backend Engineer"
        assert len(db_iceberg.projects) == 1

        # Teleperformance omitido
        assert any("Teleperformance" in s for s in summary.skipped_experiences)
        assert session.exec(select(WorkExperience).where(WorkExperience.company == "Teleperformance")).first() is None

        # Certificaciones: solo 1 nueva
        assert len(summary.added_certifications) == 1
        assert "AWS Certified Cloud Practitioner" in summary.added_certifications[0]

        # Skills: Docker clasificado en Cloud & DevOps
        assert len(summary.added_skills) == 1
        assert "Docker" in summary.added_skills[0]
