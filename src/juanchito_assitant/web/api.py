from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from juanchito_assitant.db.database import get_session
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
from juanchito_assitant.web.schemas import (
    CertificationCreate,
    CertificationUpdate,
    PersonalInfoUpdate,
    SkillCategoryCreate,
    SkillCategoryUpdate,
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
