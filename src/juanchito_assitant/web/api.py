import asyncio
from datetime import datetime
import json
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from juanchito_assitant.agents.evaluator import EvaluatorAgent
from juanchito_assitant.config import OUTPUTS_DIR
from juanchito_assitant.db.database import get_session
from juanchito_assitant.models.evaluation import EvaluationResult
from juanchito_assitant.models.job import JobRequirements
from juanchito_assitant.models.profile import (
    AdditionalAchievement,
    Certification,
    Education,
    PersonalInfo,
    PersonalProject,
    SkillCategory,
    TrackedRepo,
    WorkExperience,
    WorkProject,
)
from juanchito_assitant.tailor_engine import TailoringEngine
from juanchito_assitant.web.schemas import (
    CertificationCreate,
    CertificationUpdate,
    PersonalInfoUpdate,
    ResumeHistoryDetail,
    ResumeHistoryItem,
    SkillCategoryCreate,
    SkillCategoryUpdate,
    TailorStreamRequest,
    TrackedRepoCreate,
    TrackedRepoUpdate,
    WorkExperienceCreate,
    WorkExperienceUpdate,
    WorkProjectCreate,
    WorkProjectUpdate,
)

router = APIRouter(prefix="/api", tags=["profile"])


def get_db():
    with get_session() as session:
        yield session


# --- Perfil Consolidado ---


@router.get("/profile")
def get_consolidated_profile(db: Session = Depends(get_db)):
    """Obtiene todo el perfil del candidato consolidado en un solo payload."""
    personal = db.exec(select(PersonalInfo)).first() or PersonalInfo()

    experiences = db.exec(
        select(WorkExperience).order_by(WorkExperience.order_index)
        if hasattr(WorkExperience, "order_index")
        else select(WorkExperience)
    ).all()

    # Cargar proyectos de cada experiencia explícitamente para evitar problemas de lazy loading
    exp_data = []
    for exp in experiences:
        projects = db.exec(
            select(WorkProject)
            .where(WorkProject.work_experience_id == exp.id)
            .order_by(WorkProject.priority_weight.desc(), WorkProject.id)
        ).all()
        exp_dict = exp.model_dump()
        exp_dict["projects"] = [p.model_dump() for p in projects]
        exp_data.append(exp_dict)

    tracked_repos = db.exec(select(TrackedRepo).order_by(TrackedRepo.priority, TrackedRepo.name)).all()

    personal_projects = db.exec(select(PersonalProject)).all()
    skills = db.exec(select(SkillCategory).order_by(SkillCategory.category)).all()
    certifications = db.exec(select(Certification).order_by(Certification.issuer, Certification.title)).all()
    education = db.exec(select(Education)).all()
    achievements = db.exec(select(AdditionalAchievement)).all()

    return {
        "personal": personal.model_dump(),
        "experiences": exp_data,
        "tracked_repos": [r.model_dump() for r in tracked_repos],
        "personal_projects": [p.model_dump() for p in personal_projects],
        "skills": [s.model_dump() for s in skills],
        "certifications": [c.model_dump() for c in certifications],
        "education": [e.model_dump() for e in education],
        "additional_achievements": [a.model_dump() for a in achievements],
    }


# --- Personal Info ---


@router.put("/profile/personal")
def update_personal_info(payload: PersonalInfoUpdate, db: Session = Depends(get_db)):
    """Actualiza la información personal y datos de cabecera."""
    personal = db.exec(select(PersonalInfo)).first()
    if not personal:
        personal = PersonalInfo()
        db.add(personal)

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(personal, field, val)

    db.commit()
    db.refresh(personal)
    return personal.model_dump()


# --- Experiencia Laboral (Empresas) ---


@router.post("/profile/experiences", status_code=status.HTTP_201_CREATED)
def create_experience(payload: WorkExperienceCreate, db: Session = Depends(get_db)):
    """Crea una nueva experiencia laboral."""
    exp = WorkExperience(**payload.model_dump())
    db.add(exp)
    db.commit()
    db.refresh(exp)
    res = exp.model_dump()
    res["projects"] = []
    return res


@router.put("/profile/experiences/{exp_id}")
def update_experience(exp_id: int, payload: WorkExperienceUpdate, db: Session = Depends(get_db)):
    """Actualiza una experiencia laboral existente."""
    exp = db.get(WorkExperience, exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiencia no encontrada")

    for field, val in payload.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(exp, field, val)

    db.commit()
    db.refresh(exp)

    projects = db.exec(
        select(WorkProject)
        .where(WorkProject.work_experience_id == exp.id)
        .order_by(WorkProject.priority_weight.desc(), WorkProject.id)
    ).all()
    res = exp.model_dump()
    res["projects"] = [p.model_dump() for p in projects]
    return res


@router.delete("/profile/experiences/{exp_id}")
def delete_experience(exp_id: int, db: Session = Depends(get_db)):
    """Elimina una experiencia laboral y todas sus iniciativas técnicas asociadas."""
    exp = db.get(WorkExperience, exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiencia no encontrada")

    # Eliminar proyectos asociados
    projects = db.exec(select(WorkProject).where(WorkProject.work_experience_id == exp_id)).all()
    for proj in projects:
        db.delete(proj)

    db.delete(exp)
    db.commit()
    return {"message": "Experiencia eliminada con éxito", "id": exp_id}


# --- Iniciativas Técnicas (WorkProject) ---


@router.post("/profile/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: WorkProjectCreate, db: Session = Depends(get_db)):
    """Crea una nueva iniciativa técnica asociada a una empresa."""
    exp = db.get(WorkExperience, payload.work_experience_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiencia laboral padre no encontrada")

    proj = WorkProject(**payload.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj.model_dump()


@router.put("/profile/projects/{proj_id}")
def update_project(proj_id: int, payload: WorkProjectUpdate, db: Session = Depends(get_db)):
    """Actualiza una iniciativa técnica (nombre, tecnologías, viñetas Google XYZ)."""
    proj = db.get(WorkProject, proj_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Iniciativa técnica no encontrada")

    for field, val in payload.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(proj, field, val)

    db.commit()
    db.refresh(proj)
    return proj.model_dump()


@router.delete("/profile/projects/{proj_id}")
def delete_project(proj_id: int, db: Session = Depends(get_db)):
    """Elimina una iniciativa técnica."""
    proj = db.get(WorkProject, proj_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Iniciativa técnica no encontrada")

    db.delete(proj)
    db.commit()
    return {"message": "Iniciativa eliminada con éxito", "id": proj_id}


# --- Repositorios Seguidos (TrackedRepo) ---


@router.get("/repos")
def list_tracked_repos(db: Session = Depends(get_db)):
    """Lista todos los repositorios seguidos con su estado de sincronización."""
    repos = db.exec(select(TrackedRepo).order_by(TrackedRepo.priority, TrackedRepo.name)).all()
    return [r.model_dump() for r in repos]


@router.post("/repos", status_code=status.HTTP_201_CREATED)
def create_tracked_repo(payload: TrackedRepoCreate, db: Session = Depends(get_db)):
    """Agrega un nuevo repositorio para seguimiento en SQLite."""
    existing = db.exec(select(TrackedRepo).where(TrackedRepo.name == payload.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="El repositorio ya se encuentra registrado")

    repo = TrackedRepo(**payload.model_dump())
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo.model_dump()


@router.patch("/repos/{repo_id}/toggle")
def toggle_tracked_repo(repo_id: int, db: Session = Depends(get_db)):
    """Alterna el estado activo/inactivo de un repositorio."""
    repo = db.get(TrackedRepo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado")

    repo.is_active = not repo.is_active
    db.commit()
    db.refresh(repo)
    return repo.model_dump()


@router.put("/repos/{repo_id}")
def update_tracked_repo(repo_id: int, payload: TrackedRepoUpdate, db: Session = Depends(get_db)):
    """Actualiza configuración de un repositorio (rama, prioridad, categoría, notas)."""
    repo = db.get(TrackedRepo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado")

    for field, val in payload.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(repo, field, val)

    db.commit()
    db.refresh(repo)
    return repo.model_dump()


@router.delete("/repos/{repo_id}")
def delete_tracked_repo(repo_id: int, db: Session = Depends(get_db)):
    """Elimina un repositorio del seguimiento."""
    repo = db.get(TrackedRepo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado")

    db.delete(repo)
    db.commit()
    return {"message": "Repositorio eliminado del seguimiento", "id": repo_id}


# --- Categorías de Habilidades (Skills) ---


@router.post("/profile/skills", status_code=status.HTTP_201_CREATED)
def create_skill_category(payload: SkillCategoryCreate, db: Session = Depends(get_db)):
    """Crea una nueva categoría de habilidades."""
    cat = SkillCategory(**payload.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat.model_dump()


@router.put("/profile/skills/{category_id}")
def update_skill_category(category_id: int, payload: SkillCategoryUpdate, db: Session = Depends(get_db)):
    """Actualiza una categoría de habilidades y su lista de tags."""
    cat = db.get(SkillCategory, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    for field, val in payload.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(cat, field, val)

    db.commit()
    db.refresh(cat)
    return cat.model_dump()


@router.delete("/profile/skills/{category_id}")
def delete_skill_category(category_id: int, db: Session = Depends(get_db)):
    """Elimina una categoría de habilidades."""
    cat = db.get(SkillCategory, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    db.delete(cat)
    db.commit()
    return {"message": "Categoría eliminada", "id": category_id}


# --- Certificaciones ---


@router.post("/profile/certifications", status_code=status.HTTP_201_CREATED)
def create_certification(payload: CertificationCreate, db: Session = Depends(get_db)):
    """Agrega una certificación profesional."""
    cert = Certification(**payload.model_dump())
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert.model_dump()


@router.put("/profile/certifications/{cert_id}")
def update_certification(cert_id: int, payload: CertificationUpdate, db: Session = Depends(get_db)):
    """Actualiza una certificación profesional."""
    cert = db.get(Certification, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificación no encontrada")

    for field, val in payload.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(cert, field, val)

    db.commit()
    db.refresh(cert)
    return cert.model_dump()


@router.delete("/profile/certifications/{cert_id}")
def delete_certification(cert_id: int, db: Session = Depends(get_db)):
    """Elimina una certificación."""
    cert = db.get(Certification, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificación no encontrada")

    db.delete(cert)
    db.commit()
    return {"message": "Certificación eliminada", "id": cert_id}


# --- Diagnóstico / Health ---


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Diagnóstico de salud del servicio web y base de datos."""
    repos_count = len(db.exec(select(TrackedRepo)).all())
    exp_count = len(db.exec(select(WorkExperience)).all())
    proj_count = len(db.exec(select(WorkProject)).all())
    return {
        "status": "healthy",
        "database": "connected",
        "counts": {
            "tracked_repos": repos_count,
            "work_experiences": exp_count,
            "work_projects": proj_count,
        },
    }


# --- Tailoring Studio (SSE Streaming) ---


@router.post("/tailor/stream")
async def tailor_resume_stream(
    payload: TailorStreamRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Adapta el currículum a una vacante emitiendo progreso paso a paso mediante Server-Sent Events (SSE)."""
    if not payload.job_input.strip():
        raise HTTPException(status_code=400, detail="Debe ingresar una URL o el texto de la vacante")

    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def on_progress(event_type: str, data: dict):
        payload_data = {"type": event_type, **data}
        await queue.put(json.dumps(payload_data, ensure_ascii=False))

    async def run_pipeline():
        try:
            engine = TailoringEngine(session=db)
            await engine.run(
                job_input=payload.job_input,
                max_iterations=payload.max_iterations,
                language=payload.language,
                on_progress=on_progress,
            )
        except Exception as exc:
            error_data = {
                "type": "error",
                "message": f"Error durante la optimización: {exc!s}",
            }
            await queue.put(json.dumps(error_data, ensure_ascii=False))
        finally:
            await queue.put(None)

    async def event_generator():
        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                if await request.is_disconnected():
                    task.cancel()
                    break

                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                except TimeoutError:
                    continue

                if item is None:
                    break

                yield f"data: {item}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Historial de Currículums Adaptados ---

_ROLE_KEYWORDS = {
    "software", "backend", "frontend", "fullstack", "full", "ai", "data", "senior",
    "sr", "junior", "jr", "lead", "engineer", "developer", "architect", "scientist",
    "devops", "cloud", "machine", "intern", "associate", "tech", "systems", "qa",
}


def _parse_resume_metadata(file_path: Path) -> ResumeHistoryItem | None:
    filename = file_path.name
    if not filename.endswith(".md") or file_path.stat().st_size < 100:
        return None

    match = re.search(r"^resume_(.+)_(\d{8}_\d{6})\.md$", filename)
    if match:
        body = match.group(1)
        raw_ts = match.group(2)
        try:
            dt = datetime.strptime(raw_ts, "%Y%m%d_%H%M%S")
            created_at = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            created_at = raw_ts
    else:
        body = filename.removeprefix("resume_").removesuffix(".md")
        raw_ts = ""
        dt = datetime.fromtimestamp(file_path.stat().st_mtime)
        created_at = dt.strftime("%Y-%m-%d %H:%M")

    tokens = [t for t in re.split(r"[_]+", body) if t]
    split_idx = 1
    for idx, tok in enumerate(tokens):
        if idx > 0 and tok.lower() in _ROLE_KEYWORDS:
            split_idx = idx
            break

    company = " ".join(tokens[:split_idx]).replace("-", "").strip() or "Company"
    role = " ".join(tokens[split_idx:]).replace("-", " ").strip()
    role = re.sub(r"\s+", " ", role) or "Software Engineer"

    content = file_path.read_text(encoding="utf-8")
    headline_match = re.search(r'<div class="headline">\s*(.*?)\s*</div>', content, re.DOTALL)
    headline = headline_match.group(1).strip() if headline_match else None
    language = "es" if "## Perfil" in content or "## Experiencia" in content or "## Habilidades" in content else "en"
    word_count = len(content.split())

    # Extraer puntaje ATS del archivo JSON acompañante si existe
    ats_score: int | None = None
    ats_decision: str | None = None
    json_path = file_path.with_suffix(".json")
    if json_path.is_file():
        try:
            report_data = json.loads(json_path.read_text(encoding="utf-8"))
            final_eval = report_data.get("final_evaluation")
            if final_eval:
                ats_score = final_eval.get("total_score")
                ats_decision = final_eval.get("decision")
        except Exception:
            pass

    return ResumeHistoryItem(
        filename=filename,
        company=company,
        role=role,
        created_at=created_at,
        timestamp_raw=raw_ts,
        language=language,
        headline=headline,
        size_bytes=file_path.stat().st_size,
        word_count=word_count,
        ats_score=ats_score,
        ats_decision=ats_decision,
    )


@router.get("/tailor/history", response_model=list[ResumeHistoryItem])
def get_resume_history():
    """Retorna la lista de currículums adaptados generados previamente en data/outputs/."""
    if not OUTPUTS_DIR.exists():
        return []

    items: list[ResumeHistoryItem] = []
    for file_path in OUTPUTS_DIR.glob("*.md"):
        item = _parse_resume_metadata(file_path)
        if item:
            items.append(item)

    items.sort(key=lambda x: x.timestamp_raw or x.created_at, reverse=True)
    return items


@router.get("/tailor/history/{filename}", response_model=ResumeHistoryDetail)
def get_resume_history_detail(filename: str):
    """Retorna el contenido completo en Markdown y metadatos de un currículum generado previamente."""
    if ".." in filename or "/" in filename or "\\" in filename or not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    target_file = OUTPUTS_DIR / filename
    if not target_file.is_file():
        raise HTTPException(status_code=404, detail="Currículum no encontrado")

    item = _parse_resume_metadata(target_file)
    if not item:
        raise HTTPException(status_code=400, detail="El archivo solicitado no es un currículum válido")

    content = target_file.read_text(encoding="utf-8")

    evaluation: EvaluationResult | None = None
    json_path = target_file.with_suffix(".json")
    if json_path.is_file():
        try:
            report_data = json.loads(json_path.read_text(encoding="utf-8"))
            if "final_evaluation" in report_data and report_data["final_evaluation"]:
                evaluation = EvaluationResult.model_validate(report_data["final_evaluation"])
        except Exception:
            pass

    return ResumeHistoryDetail(
        **item.model_dump(),
        markdown=content,
        evaluation=evaluation,
    )


@router.post("/tailor/history/{filename}/audit", response_model=ResumeHistoryDetail)
async def audit_resume_history(filename: str):
    """Ejecuta una auditoría ATS con EvaluatorAgent sobre un currículum existente y guarda su .json."""
    if ".." in filename or "/" in filename or "\\" in filename or not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    target_file = OUTPUTS_DIR / filename
    if not target_file.is_file():
        raise HTTPException(status_code=404, detail="Currículum no encontrado")

    item = _parse_resume_metadata(target_file)
    if not item:
        raise HTTPException(status_code=400, detail="El archivo solicitado no es un currículum válido")

    content = target_file.read_text(encoding="utf-8")
    json_path = target_file.with_suffix(".json")

    job = None
    if json_path.is_file():
        try:
            report_data = json.loads(json_path.read_text(encoding="utf-8"))
            if "job" in report_data and report_data["job"]:
                job = JobRequirements.model_validate(report_data["job"])
        except Exception:
            pass

    if not job:
        job = JobRequirements(
            job_title=item.role,
            company_name=item.company,
            role_summary=item.headline or f"{item.role} at {item.company}",
            must_have_skills=[],
            nice_to_have_skills=[],
            ats_keywords=[],
            core_responsibilities=[],
        )

    evaluator = EvaluatorAgent()
    evaluation = await evaluator.evaluate(job=job, resume_markdown=content, language=item.language)

    report_payload = {
        "job": job.model_dump(mode="json"),
        "final_markdown": content,
        "final_evaluation": evaluation.model_dump(mode="json"),
        "language": item.language,
    }
    json_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    item_dict = item.model_dump()
    item_dict["ats_score"] = evaluation.total_score
    item_dict["ats_decision"] = evaluation.decision

    return ResumeHistoryDetail(
        **item_dict,
        markdown=content,
        evaluation=evaluation,
    )


