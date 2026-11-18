from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine, select

from juanchito_assitant.config import DB_PATH, OUTPUTS_DIR
from juanchito_assitant.db.database import get_engine
from juanchito_assitant.db.resume_store import sync_outputs_dir_to_db, upsert_generated_resume
from juanchito_assitant.models.profile import (
    AdditionalAchievement,
    Certification,
    Education,
    GeneratedResume,
    PersonalInfo,
    PersonalProject,
    SkillCategory,
    TrackedRepo,
    WorkExperience,
    WorkProject,
)


def push_local_to_target_db(
    target_url: str,
    source_db_path: Path = DB_PATH,
    outputs_dir: Path = OUTPUTS_DIR,
) -> dict[str, int]:
    """Sincroniza de forma idempotente (upsert) todo el perfil local y CVs generados hacia la DB remota."""
    if not target_url or not target_url.strip():
        raise ValueError("Se requiere una URL de base de datos destino (DATABASE_URL o --target-url).")

    source_engine = create_engine(
        f"sqlite:///{source_db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    target_engine = get_engine(database_url=target_url)

    SQLModel.metadata.create_all(source_engine)
    SQLModel.metadata.create_all(target_engine)

    counts = {
        "personal": 0,
        "experiences": 0,
        "work_projects": 0,
        "personal_projects": 0,
        "tracked_repos": 0,
        "certifications": 0,
        "education": 0,
        "skills": 0,
        "achievements": 0,
        "generated_resumes": 0,
    }

    with Session(source_engine, expire_on_commit=False) as src_sess:
        # 1. Asegurar que todos los CVs en data/outputs/ estén sincronizados en la fuente primero
        if outputs_dir.exists():
            sync_outputs_dir_to_db(src_sess, outputs_dir)

        with Session(target_engine, expire_on_commit=False) as dst_sess:
            # --- PersonalInfo ---
            src_personal = src_sess.exec(select(PersonalInfo)).first()
            if src_personal:
                dst_personal = dst_sess.exec(select(PersonalInfo)).first()
                if not dst_personal:
                    dst_personal = PersonalInfo()
                for field in (
                    "full_name",
                    "timezone",
                    "location",
                    "email",
                    "phone",
                    "linkedin",
                    "github",
                    "headline",
                    "profile_summary",
                    "extra_variables",
                ):
                    setattr(dst_personal, field, getattr(src_personal, field))
                dst_sess.add(dst_personal)
                dst_sess.commit()
                counts["personal"] = 1

            # --- WorkExperience & WorkProject ---
            src_experiences = src_sess.exec(select(WorkExperience)).all()
            for src_exp in src_experiences:
                dst_exp = dst_sess.exec(
                    select(WorkExperience).where(
                        WorkExperience.company == src_exp.company,
                        WorkExperience.role == src_exp.role,
                    )
                ).first()
                if not dst_exp:
                    dst_exp = WorkExperience(
                        company=src_exp.company,
                        role=src_exp.role,
                        location=src_exp.location,
                        start_date=src_exp.start_date,
                        end_date=src_exp.end_date,
                        is_current=src_exp.is_current,
                        order_index=src_exp.order_index,
                    )
                    dst_sess.add(dst_exp)
                    dst_sess.commit()
                    dst_sess.refresh(dst_exp)
                else:
                    dst_exp.location = src_exp.location
                    dst_exp.start_date = src_exp.start_date
                    dst_exp.end_date = src_exp.end_date
                    dst_exp.is_current = src_exp.is_current
                    dst_exp.order_index = src_exp.order_index
                    dst_sess.add(dst_exp)
                    dst_sess.commit()
                    dst_sess.refresh(dst_exp)
                counts["experiences"] += 1

                src_projects = src_sess.exec(
                    select(WorkProject).where(WorkProject.work_experience_id == src_exp.id)
                ).all()
                for src_proj in src_projects:
                    dst_proj = dst_sess.exec(
                        select(WorkProject).where(
                            WorkProject.work_experience_id == dst_exp.id,
                            WorkProject.name == src_proj.name,
                        )
                    ).first()
                    if not dst_proj:
                        dst_proj = WorkProject(
                            work_experience_id=dst_exp.id,
                            name=src_proj.name,
                            bullets=list(src_proj.bullets),
                            technologies=list(src_proj.technologies),
                            priority_weight=src_proj.priority_weight,
                        )
                    else:
                        dst_proj.bullets = list(src_proj.bullets)
                        dst_proj.technologies = list(src_proj.technologies)
                        dst_proj.priority_weight = src_proj.priority_weight
                    dst_sess.add(dst_proj)
                    counts["work_projects"] += 1
                dst_sess.commit()

            # --- PersonalProject ---
            for src_pp in src_sess.exec(select(PersonalProject)).all():
                dst_pp = dst_sess.exec(
                    select(PersonalProject).where(PersonalProject.name == src_pp.name)
                ).first()
                if not dst_pp:
                    dst_pp = PersonalProject(name=src_pp.name)
                for field in (
                    "repo_url",
                    "branch",
                    "description",
                    "bullets",
                    "technologies",
                    "has_readme",
                    "suggested_readme",
                    "last_pushed_at",
                ):
                    setattr(dst_pp, field, getattr(src_pp, field))
                dst_sess.add(dst_pp)
                counts["personal_projects"] += 1
            dst_sess.commit()

            # --- TrackedRepo ---
            for src_repo in src_sess.exec(select(TrackedRepo)).all():
                dst_repo = dst_sess.exec(
                    select(TrackedRepo).where(TrackedRepo.name == src_repo.name)
                ).first()
                if not dst_repo:
                    dst_repo = TrackedRepo(name=src_repo.name)
                for field in ("branch", "is_active", "priority", "category", "notes"):
                    setattr(dst_repo, field, getattr(src_repo, field))
                dst_sess.add(dst_repo)
                counts["tracked_repos"] += 1
            dst_sess.commit()

            # --- Certification ---
            for src_cert in src_sess.exec(select(Certification)).all():
                dst_cert = dst_sess.exec(
                    select(Certification).where(
                        Certification.issuer == src_cert.issuer,
                        Certification.title == src_cert.title,
                    )
                ).first()
                if not dst_cert:
                    dst_cert = Certification(
                        issuer=src_cert.issuer,
                        title=src_cert.title,
                        issue_date=src_cert.issue_date,
                    )
                else:
                    dst_cert.issue_date = src_cert.issue_date
                dst_sess.add(dst_cert)
                counts["certifications"] += 1
            dst_sess.commit()

            # --- Education ---
            for src_edu in src_sess.exec(select(Education)).all():
                dst_edu = dst_sess.exec(
                    select(Education).where(
                        Education.institution == src_edu.institution,
                        Education.degree == src_edu.degree,
                    )
                ).first()
                if not dst_edu:
                    dst_edu = Education(
                        institution=src_edu.institution,
                        degree=src_edu.degree,
                        date_range=src_edu.date_range,
                        location=src_edu.location,
                    )
                else:
                    dst_edu.date_range = src_edu.date_range
                    dst_edu.location = src_edu.location
                dst_sess.add(dst_edu)
                counts["education"] += 1
            dst_sess.commit()

            # --- SkillCategory ---
            for src_skill in src_sess.exec(select(SkillCategory)).all():
                dst_skill = dst_sess.exec(
                    select(SkillCategory).where(SkillCategory.category == src_skill.category)
                ).first()
                if not dst_skill:
                    dst_skill = SkillCategory(
                        category=src_skill.category,
                        skills=list(src_skill.skills),
                    )
                else:
                    dst_skill.skills = list(src_skill.skills)
                dst_sess.add(dst_skill)
                counts["skills"] += 1
            dst_sess.commit()

            # --- AdditionalAchievement ---
            for src_ach in src_sess.exec(select(AdditionalAchievement)).all():
                dst_ach = dst_sess.exec(
                    select(AdditionalAchievement).where(
                        AdditionalAchievement.category == src_ach.category,
                        AdditionalAchievement.title == src_ach.title,
                    )
                ).first()
                if not dst_ach:
                    dst_ach = AdditionalAchievement(
                        category=src_ach.category,
                        title=src_ach.title,
                        institution=src_ach.institution,
                        location=src_ach.location,
                        date_range=src_ach.date_range,
                        description_bullets=list(src_ach.description_bullets),
                        links=list(src_ach.links),
                    )
                else:
                    dst_ach.institution = src_ach.institution
                    dst_ach.location = src_ach.location
                    dst_ach.date_range = src_ach.date_range
                    dst_ach.description_bullets = list(src_ach.description_bullets)
                    dst_ach.links = list(src_ach.links)
                dst_sess.add(dst_ach)
                counts["achievements"] += 1
            dst_sess.commit()

            # --- GeneratedResume (Batch Upsert para baja latencia en la nube) ---
            existing_by_filename = {
                r.filename: r for r in dst_sess.exec(select(GeneratedResume)).all()
            }
            for src_res in src_sess.exec(select(GeneratedResume)).all():
                dst_res = existing_by_filename.get(src_res.filename)
                if dst_res is None:
                    dst_res = GeneratedResume(
                        filename=src_res.filename,
                        company=src_res.company,
                        role=src_res.role,
                        language=src_res.language,
                        headline=src_res.headline,
                        markdown_content=src_res.markdown_content,
                        word_count=src_res.word_count,
                        size_bytes=src_res.size_bytes,
                        ats_score=src_res.ats_score,
                        ats_decision=src_res.ats_decision,
                        job_payload=dict(src_res.job_payload or {}),
                        evaluation_payload=dict(src_res.evaluation_payload) if src_res.evaluation_payload else None,
                        created_at=src_res.created_at,
                        timestamp_raw=src_res.timestamp_raw,
                    )
                else:
                    dst_res.company = src_res.company
                    dst_res.role = src_res.role
                    dst_res.language = src_res.language
                    dst_res.headline = src_res.headline
                    dst_res.markdown_content = src_res.markdown_content
                    dst_res.word_count = src_res.word_count
                    dst_res.size_bytes = src_res.size_bytes
                    dst_res.ats_score = src_res.ats_score
                    dst_res.ats_decision = src_res.ats_decision
                    dst_res.job_payload = dict(src_res.job_payload or {})
                    dst_res.evaluation_payload = (
                        dict(src_res.evaluation_payload) if src_res.evaluation_payload else None
                    )
                    dst_res.created_at = src_res.created_at
                    dst_res.timestamp_raw = src_res.timestamp_raw
                dst_sess.add(dst_res)
                counts["generated_resumes"] += 1
            dst_sess.commit()

    return counts
