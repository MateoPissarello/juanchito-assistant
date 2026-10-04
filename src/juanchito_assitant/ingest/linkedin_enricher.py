import re
from sqlmodel import Session, select

from juanchito_assitant.models.linkedin import LinkedInEnrichmentSummary, LinkedInProfileExtract
from juanchito_assitant.models.profile import (
    Certification,
    Education,
    SkillCategory,
    WorkExperience,
    WorkProject,
)


def _normalize_str(text: str) -> str:
    """Normaliza un string a minúsculas sin signos de puntuación para comparaciones difusas."""
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _is_company_match(company_a: str, company_b: str) -> bool:
    """Verifica si dos nombres de empresa hacen referencia a la misma entidad.

    Ejemplos:
        'Blend' y 'Blend360 Colombia' -> True
        'PhenoScience' y 'PhenoScience' -> True
        'Icebergdata' y 'Blend360 Colombia' -> False
    """
    norm_a = _normalize_str(company_a)
    norm_b = _normalize_str(company_b)
    if not norm_a or not norm_b:
        return False
    return norm_a in norm_b or norm_b in norm_a


def _is_cert_match(cert_a: str, cert_b: str) -> bool:
    """Verifica si dos títulos de certificación coinciden sustancialmente."""
    norm_a = _normalize_str(cert_a)
    norm_b = _normalize_str(cert_b)
    if not norm_a or not norm_b:
        return False
    return norm_a in norm_b or norm_b in norm_a


def enrich_profile_from_linkedin(
    session: Session,
    extract: LinkedInProfileExtract,
    dry_run: bool = False,
    include_non_technical: bool = False,
) -> LinkedInEnrichmentSummary:
    """Enriquece el perfil existente en la base de datos con datos de LinkedIn sin destruir información previa.

    Args:
        session: Sesión activa de SQLModel.
        extract: Extracción semántica obtenida del PDF.
        dry_run: Si es True, no ejecuta commit en la base de datos.
        include_non_technical: Si es True, incluye roles no técnicos (como atención al cliente).

    Returns:
        LinkedInEnrichmentSummary con el detalle de adiciones y omisiones.
    """
    summary = LinkedInEnrichmentSummary()

    # 1. Procesar Experiencia Laboral
    existing_work = session.exec(select(WorkExperience)).all()

    for exp in extract.experiences:
        # Filtrar roles no técnicos si no se solicita incluirlos
        if not exp.is_technical and not include_non_technical:
            summary.skipped_experiences.append(f"{exp.company} - {exp.role} (Omitido: Rol no técnico)")
            continue

        # Buscar coincidencia con empresas ya registradas en la DB
        matched_exp = next(
            (w for w in existing_work if _is_company_match(w.company, exp.company)),
            None,
        )

        if matched_exp:
            summary.existing_experiences.append(
                f"{matched_exp.company} (Ya registrada con {len(matched_exp.projects)} iniciativas. Datos preservados)."
            )
            # Si faltaba ubicación o fechas y LinkedIn las provee, complementar sin tocar proyectos
            if not matched_exp.location and exp.location:
                matched_exp.location = exp.location
                summary.updated_fields.append(f"Ubicación actualizada para {matched_exp.company}: {exp.location}")
        else:
            # Nueva empresa detectada (ej. Icebergdata)
            new_work = WorkExperience(
                role=exp.role,
                company=exp.company,
                location=exp.location or "Bogotá, Colombia",
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                order_index=len(existing_work),
            )
            session.add(new_work)
            session.flush()  # Para obtener new_work.id

            # Crear proyecto técnico principal para la nueva empresa
            proj_name = f"{exp.company} Core"
            new_proj = WorkProject(
                work_experience_id=new_work.id,
                name=proj_name,
                bullets=exp.bullets,
                technologies=exp.technologies,
                priority_weight=1,
            )
            session.add(new_proj)
            summary.added_experiences.append(
                f"{exp.company} | {exp.role} ({len(exp.bullets)} viñetas, {len(exp.technologies)} tecnologías)"
            )

    # 2. Procesar Certificaciones
    existing_certs = session.exec(select(Certification)).all()
    for cert in extract.certifications:
        matched_cert = next(
            (c for c in existing_certs if _is_cert_match(c.title, cert.title)),
            None,
        )
        if not matched_cert:
            new_cert = Certification(
                issuer=cert.issuer or "Online Platform",
                title=cert.title,
                issue_date=cert.issue_date or "N/A",
            )
            session.add(new_cert)
            summary.added_certifications.append(f"{cert.title} ({cert.issuer})")

    # 3. Procesar Educación
    existing_edu = session.exec(select(Education)).all()
    for edu in extract.education:
        matched_edu = next(
            (e for e in existing_edu if _normalize_str(e.institution) in _normalize_str(edu.institution) or _normalize_str(edu.institution) in _normalize_str(e.institution)),
            None,
        )
        if not matched_edu:
            new_edu = Education(
                institution=edu.institution,
                degree=edu.degree,
                date_range=edu.date_range or "N/A",
                location=edu.location or "Bogotá, Colombia",
            )
            session.add(new_edu)
            summary.added_education.append(f"{edu.institution} - {edu.degree}")

    # 4. Procesar Habilidades (Skills)
    existing_categories = session.exec(select(SkillCategory)).all()
    existing_skill_set = {
        s.lower() for cat in existing_categories for s in cat.skills
    }

    # Mapa heurístico de clasificación de skills
    category_map = {
        "Languages": ["python", "typescript", "javascript", "java", "sql", "c++", "c#", "go", "rust", "html", "css"],
        "Backend": ["fastapi", "django", "flask", "node", "rest", "graphql", "microservices", "sqlalchemy", "back-end", "backend"],
        "Cloud & DevOps": ["aws", "docker", "kubernetes", "eks", "fargate", "lambda", "terraform", "ci/cd", "git", "cloud"],
        "Data & AI": ["machine learning", "ia generativa", "generative ai", "rag", "bedrock", "deep learning", "opencv", "scraping", "pandas"],
        "Databases & Storage": ["postgresql", "mysql", "redis", "dynamodb", "mongodb", "sqlite", "s3"],
    }

    for skill in extract.skills:
        skill_lower = skill.strip().lower()
        if skill_lower in existing_skill_set or not skill_lower:
            continue

        # Buscar la categoría más adecuada
        target_category_name = "Other / Tools"
        for cat_name, keywords in category_map.items():
            if any(kw in skill_lower for kw in keywords):
                target_category_name = cat_name
                break

        # Buscar o crear la categoría correspondiente
        cat_obj = next((c for c in existing_categories if c.category.lower() == target_category_name.lower()), None)
        if not cat_obj:
            cat_obj = SkillCategory(category=target_category_name, skills=[])
            session.add(cat_obj)
            existing_categories.append(cat_obj)

        if skill not in cat_obj.skills:
            cat_obj.skills = list(cat_obj.skills) + [skill]
            existing_skill_set.add(skill_lower)
            summary.added_skills.append(f"{skill} (Categoría: {cat_obj.category})")

    if not dry_run:
        session.commit()
    else:
        session.rollback()

    return summary
