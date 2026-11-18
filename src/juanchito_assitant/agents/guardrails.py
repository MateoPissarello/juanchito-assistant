import logging
import re
from juanchito_assitant.agents.cv_writer import (
    TailoredExperience,
    TailoredInitiative,
    TailoredProject,
    TailoredResumeContent,
)
from juanchito_assitant.agents.matcher import (
    COMMON_TECHS,
    MatchedContext,
    curate_project_technologies,
    extract_key_terms,
    matches_term,
)
from juanchito_assitant.models.job import JobRequirements

logger = logging.getLogger(__name__)

# Conceptos y metodologías estándar de ingeniería de software aceptables universalmente
ALLOWED_GENERIC_CONCEPTS = {
    "rest api",
    "rest apis",
    "rest api design",
    "microservices",
    "cloud-native",
    "cloud-native applications",
    "serverless",
    "serverless architecture",
    "clean code",
    "clean architecture",
    "agile",
    "scrum",
    "git",
    "ci/cd",
    "ci/cd pipelines",
    "testing",
    "unit testing",
    "integration testing",
    "database design",
    "data modeling",
    "data pipelines",
    "distributed systems",
    "event-driven",
    "event-driven architecture",
    "object-oriented programming",
    "oop",
    "solid",
    "software architecture",
    "api design",
    "devops",
    "system design",
    "third-party api integrations",
    "webhook implementations",
    "webhooks",
    "infrastructure as code",
    "iac",
    "backend",
    "frontend",
    "full-stack",
    "scalability",
    "high availability",
    "observability",
    "monitoring",
    "security",
    "authentication",
    "authorization",
    "performance optimization",
    "code review",
    "design patterns",
    "ai applications",
    "enterprise integrations",
    "cloud platforms",
    "json",
    "apis rest",
    "api rest",
    "microservicios",
    "arquitectura de microservicios",
    "integraciones",
    "integración de servicios",
    "integracion de servicios",
    "arquitectura limpia",
    "código limpio",
    "codigo limpio",
    "pruebas unitarias",
    "pruebas de integración",
    "pruebas de integracion",
    "despliegue continuo",
    "integración continua",
    "integracion continua",
    "sistemas distribuidos",
    "arquitectura orientada a eventos",
    "alta disponibilidad",
    "escalabilidad",
    "observabilidad",
    "monitoreo",
    "seguridad",
    "autenticación",
    "autenticacion",
    "autorización",
    "autorizacion",
    "optimización de rendimiento",
    "optimizacion de rendimiento",
    "patrones de diseño",
}

# Catálogo extendido de tecnologías concretas para detectar alucinaciones en viñetas incluso si no venían en el Job
KNOWN_TECH_CATALOG = COMMON_TECHS | {
    "snowflake",
    "databricks",
    "spark",
    "apache spark",
    "hadoop",
    "airflow",
    "apache airflow",
    "bigquery",
    "redshift",
    "azure",
    "microsoft azure",
    "azure functions",
    "azure devops",
    "gcp",
    "google cloud",
    "kafka",
    "apache kafka",
    "rabbitmq",
    "golang",
    "rust",
    "ruby",
    "rails",
    "ruby on rails",
    "php",
    "laravel",
    "csharp",
    "c#",
    ".net",
    "angular",
    "svelte",
    "vue",
    "flutter",
    "swift",
    "kotlin",
    "cassandra",
    "neo4j",
    "elasticsearch",
    "opensearch",
    "splunk",
    "datadog",
    "prometheus",
    "grafana",
    "ansible",
    "jenkins",
    "circleci",
    "helm",
    "istio",
    "vault",
    "consul",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "pandas",
    "numpy",
    "celery",
    "grpc",
    "supabase",
    "firebase",
    "pinecone",
    "weaviate",
    "milvus",
    "qdrant",
    "chromadb",
    "temporal",
    "cobol",
    "scala",
    "elixir",
}


class FactualGuardrail:
    """Validador programático determinista para asegurar factualidad estricta y prevenir alucinaciones."""

    @classmethod
    def build_tech_universe(cls, ctx: MatchedContext) -> tuple[set[str], str]:
        """Construye el universo de tecnologías verificadas y el corpus textual completo del candidato desde SQLite."""
        tech_universe: set[str] = set()
        raw_tech_items: list[str] = []
        corpus_parts: list[str] = []

        for cat in ctx.skills:
            raw_tech_items.extend(cat.skills)
            corpus_parts.extend(cat.skills)
        for w in ctx.work_matches:
            raw_tech_items.extend(w.technologies)
            corpus_parts.append(w.project_name)
            corpus_parts.extend(w.technologies)
            corpus_parts.extend(w.bullets)
        for p in ctx.github_matches:
            raw_tech_items.extend(p.technologies)
            corpus_parts.append(p.name)
            if p.description:
                corpus_parts.append(p.description)
            if p.category:
                corpus_parts.append(p.category)
            corpus_parts.extend(p.technologies)
            corpus_parts.extend(p.bullets)
        for c in ctx.certifications:
            corpus_parts.append(f"{c.issuer} {c.title}")

        for raw in raw_tech_items:
            clean = raw.strip().lower()
            if not clean:
                continue
            tech_universe.add(clean)
            tokens = [p.strip() for p in re.split(r"[,/()&+\n]+", clean) if len(p.strip()) >= 2]
            for tok in tokens:
                tech_universe.add(tok)

        full_corpus_lower = " ".join(corpus_parts).lower()

        # Agregar también cualquier tecnología conocida que aparezca explícitamente en las viñetas reales de SQLite
        for known in KNOWN_TECH_CATALOG:
            pattern = r"\b" + re.escape(known) + r"\b"
            if re.search(pattern, full_corpus_lower):
                tech_universe.add(known)

        return tech_universe, full_corpus_lower

    @classmethod
    def classify_job_skills(
        cls,
        job: JobRequirements,
        ctx: MatchedContext,
    ) -> tuple[list[str], list[str]]:
        """Clasifica las habilidades requeridas por la vacante en:
        - owned_job_skills: Habilidades de la vacante que el candidato SÍ posee en su perfil de SQLite.
        - unowned_job_skills: Habilidades de la vacante que el candidato NO posee en SQLite (brechas reales).
        """
        tech_universe, full_corpus_lower = cls.build_tech_universe(ctx)

        raw_job_skills = (
            list(job.must_have_skills)
            + list(job.nice_to_have_skills)
            + list(job.ats_keywords)
        )
        extracted_terms = extract_key_terms(raw_job_skills)

        # Conservar también términos explícitos cortos de must_have y nice_to_have (descomponiendo pares con '/' como 'Python/FastAPI')
        candidates_to_check: list[str] = []
        seen_lower: set[str] = set()
        raw_explicit: list[str] = []
        for raw_item in list(job.must_have_skills) + list(job.nice_to_have_skills):
            r_clean = raw_item.strip()
            if "/" in r_clean and r_clean.lower() not in ("ci/cd", "i/o", "tcp/ip", "pl/sql"):
                for sub_part in r_clean.split("/"):
                    if sub_part.strip():
                        raw_explicit.append(sub_part.strip())
            else:
                raw_explicit.append(r_clean)

        for item in raw_explicit + extracted_terms:
            clean = item.strip()
            low = clean.lower()
            if not clean or len(clean) < 2 or len(clean.split()) > 4 or low in seen_lower:
                continue
            seen_lower.add(low)
            candidates_to_check.append(clean)

        owned_job_skills: list[str] = []
        unowned_job_skills: list[str] = []

        for skill in candidates_to_check:
            s_low = skill.lower().strip()
            if s_low in ALLOWED_GENERIC_CONCEPTS:
                continue
            if matches_term(s_low, full_corpus_lower, tech_universe):
                owned_job_skills.append(skill)
            else:
                unowned_job_skills.append(skill)

        return owned_job_skills, unowned_job_skills

    @classmethod
    def _build_forbidden_techs(
        cls,
        ctx: MatchedContext,
        tech_universe: set[str],
        full_corpus_lower: str,
    ) -> list[str]:
        """Construye la lista ordenada de tecnologías prohibidas (no poseídas por el candidato)."""
        _, unowned_job_skills = cls.classify_job_skills(ctx.target_job, ctx)
        forbidden: set[str] = set()

        for u in unowned_job_skills:
            u_low = u.lower().strip()
            if u_low and u_low not in ALLOWED_GENERIC_CONCEPTS and u_low not in tech_universe:
                forbidden.add(u_low)
                # También descomponer sub-tokens si son tecnologías conocidas
                for sub in re.split(r"[,/()&+\s]+", u_low):
                    sub = sub.strip()
                    if sub in KNOWN_TECH_CATALOG and sub not in tech_universe:
                        forbidden.add(sub)

        for known in KNOWN_TECH_CATALOG:
            if known not in tech_universe and known not in ALLOWED_GENERIC_CONCEPTS:
                if not matches_term(known, full_corpus_lower, tech_universe):
                    forbidden.add(known)

        # Ordenar de más largo a más corto para priorizar frases compuestas ("azure functions" antes de "azure")
        return sorted(forbidden, key=len, reverse=True)

    @classmethod
    def _detect_forbidden_tech_in_bullet(
        cls,
        bullet: str,
        forbidden_techs: list[str],
    ) -> str | None:
        """Retorna el nombre de la primera tecnología no poseída detectada en una viñeta, o None si es limpia."""
        b_low = bullet.lower()
        for f_tech in forbidden_techs:
            # Regex con límites de palabra; soporta caracteres especiales como c# o .net
            if re.match(r"^[\w\s\-]+$", f_tech):
                pattern = r"\b" + re.escape(f_tech) + r"\b"
            else:
                pattern = r"(?<!\w)" + re.escape(f_tech) + r"(?!\w)"
            if re.search(pattern, b_low):
                return f_tech
        return None

    @classmethod
    def _sanitize_bullets(
        cls,
        generated_bullets: list[str],
        original_bullets: list[str],
        entity_label: str,
        forbidden_techs: list[str],
        alerts: list[str],
        language: str = "en",
    ) -> list[str]:
        """Inspecciona cada viñeta generada; si contiene tecnologías alucinadas, restaura la viñeta original verificada."""
        from juanchito_assitant.rendering.resume_renderer import ResumeRenderer

        is_es = language.lower() == "es"
        sanitized: list[str] = []
        used_originals: set[str] = set()

        for b in generated_bullets:
            bad_tech = cls._detect_forbidden_tech_in_bullet(b, forbidden_techs)
            if bad_tech is None:
                sanitized.append(ResumeRenderer.localize_bullet_es(b) if is_es else b)
                used_originals.add(b.strip().lower())
            else:
                alert_msg = (
                    f"Alucinación bloqueada en viñeta de '{entity_label}': "
                    f"tecnología no poseída '{bad_tech}' detectada."
                )
                alerts.append(alert_msg)
                logger.warning(f"[FACTUAL GUARDRAIL] {alert_msg}")

                # Buscar una viñeta original verificada de SQLite que no haya sido usada aún
                for orig in original_bullets:
                    if orig.strip().lower() not in used_originals:
                        fallback_bullet = ResumeRenderer.localize_bullet_es(orig) if is_es else orig
                        sanitized.append(fallback_bullet)
                        used_originals.add(orig.strip().lower())
                        break

        if not sanitized and original_bullets:
            sanitized = [
                ResumeRenderer.localize_bullet_es(orig) if is_es else orig
                for orig in original_bullets[:3]
            ]

        return sanitized

    @classmethod
    def apply(
        cls,
        content: TailoredResumeContent,
        ctx: MatchedContext,
        language: str = "en",
    ) -> tuple[TailoredResumeContent, list[str]]:
        """Aplica filtros deterministas a proyectos, experiencias, viñetas y habilidades.

        Args:
            content: Objeto estructurado emitido por el WriterAgent.
            ctx: Contexto fáctico verificado del candidato desde SQLite.

        Returns:
            Tupla (contenido_saneado, alertas_de_guardrail).
        """
        alerts: list[str] = []
        tech_universe, full_corpus_lower = cls.build_tech_universe(ctx)
        forbidden_techs = cls._build_forbidden_techs(ctx, tech_universe, full_corpus_lower)

        # -------------------------------------------------------------
        # 1. Guardrail de Proyectos Técnicos Personales (GitHub)
        # -------------------------------------------------------------
        # Solo se permiten proyectos cuyos nombres correspondan a los proyectos reales del candidato
        valid_projects = {p.name.strip().lower(): p for p in ctx.github_matches}
        sanitized_projects: list[TailoredProject] = []

        for p in content.projects:
            p_name_clean = p.name.strip().lower()
            # Búsqueda exacta o coincidencia por prefijo/subcadena
            matched_real = valid_projects.get(p_name_clean)
            if not matched_real:
                # Verificar si algún nombre real está contenido en el propuesto
                for r_name, r_proj in valid_projects.items():
                    if r_name in p_name_clean or p_name_clean in r_name:
                        matched_real = r_proj
                        break

            if matched_real:
                # El proyecto existe en SQLite
                p.repo_url = matched_real.repo_url or p.repo_url
                if not p.year:
                    p.year = matched_real.year

                # Saneamiento y curación de tecnologías del proyecto (máx 6 relevantes, sin librerías transitivas)
                clean_proj_techs: list[str] = []
                for t in p.technologies:
                    t_low = t.strip().lower()
                    bad_t = cls._detect_forbidden_tech_in_bullet(t_low, forbidden_techs)
                    if bad_t is None and (t_low in tech_universe or t_low in ALLOWED_GENERIC_CONCEPTS):
                        clean_proj_techs.append(t)
                    else:
                        alert_msg = f"Tecnología no verificada '{t}' purgada del proyecto '{p.name}'"
                        alerts.append(alert_msg)
                        logger.warning(f"[FACTUAL GUARDRAIL] {alert_msg}")
                base_proj_techs = clean_proj_techs if clean_proj_techs else list(matched_real.technologies)
                p.technologies = curate_project_technologies(
                    base_proj_techs,
                    job=ctx.target_job,
                    max_techs=6,
                )

                # Saneamiento de viñetas del proyecto
                p.bullets = cls._sanitize_bullets(
                    generated_bullets=p.bullets,
                    original_bullets=matched_real.bullets,
                    entity_label=p.name,
                    forbidden_techs=forbidden_techs,
                    alerts=alerts,
                    language=language,
                )
                sanitized_projects.append(p)
            else:
                alert_msg = f"Proyecto no existente purgado: '{p.name}'"
                alerts.append(alert_msg)
                logger.warning(f"[FACTUAL GUARDRAIL] {alert_msg}")

        content.projects = sanitized_projects

        # -------------------------------------------------------------
        # 2. Guardrail de Empresas, Iniciativas y Viñetas Laborales
        # -------------------------------------------------------------
        valid_companies = {w.company.strip().lower(): w for w in ctx.work_matches}
        sanitized_experiences: list[TailoredExperience] = []

        for exp in content.experiences:
            exp_comp_clean = exp.company.strip().lower()
            matched_comp = None
            for c_name in valid_companies:
                if c_name in exp_comp_clean or exp_comp_clean in c_name:
                    matched_comp = c_name
                    break

            if matched_comp:
                # Empresa válida en el perfil
                real_inits_for_comp = [
                    w for w in ctx.work_matches if w.company.strip().lower() == matched_comp
                ]
                valid_init_names = {w.project_name.strip().lower(): w for w in real_inits_for_comp}

                sanitized_inits: list[TailoredInitiative] = []
                matched_real_names: set[str] = set()
                for init in exp.initiatives:
                    init_clean = init.name.strip().lower()
                    init_matched = None
                    for r_name, r_init in valid_init_names.items():
                        if r_name in init_clean or init_clean in r_name:
                            init_matched = r_init
                            matched_real_names.add(r_name)
                            break

                    if init_matched:
                        init.bullets = cls._sanitize_bullets(
                            generated_bullets=init.bullets,
                            original_bullets=init_matched.bullets,
                            entity_label=init.name,
                            forbidden_techs=forbidden_techs,
                            alerts=alerts,
                            language=language,
                        )
                        sanitized_inits.append(init)
                    else:
                        alert_msg = f"Iniciativa no verificable purgada: '{init.name}' en '{exp.company}'"
                        alerts.append(alert_msg)
                        logger.warning(f"[FACTUAL GUARDRAIL] {alert_msg}")

                # Si el LLM omitió alguna iniciativa laboral seleccionada por el Matcher (ej. Zammad on Kubernetes), restaurarla
                from juanchito_assitant.rendering.resume_renderer import ResumeRenderer

                is_es = language.lower() == "es"
                for r in real_inits_for_comp:
                    r_key = r.project_name.strip().lower()
                    if r_key not in matched_real_names:
                        restored_name = (
                            ResumeRenderer.localize_initiative_name_es(r.project_name)
                            if is_es
                            else r.project_name
                        )
                        restored_bullets = (
                            [ResumeRenderer.localize_bullet_es(b) for b in r.bullets[:2]]
                            if is_es
                            else r.bullets[:2]
                        )
                        sanitized_inits.append(
                            TailoredInitiative(name=restored_name, bullets=restored_bullets)
                        )
                        matched_real_names.add(r_key)

                exp.initiatives = sanitized_inits
                sanitized_experiences.append(exp)
            else:
                alert_msg = f"Empresa no verificable purgada: '{exp.company}'"
                alerts.append(alert_msg)
                logger.warning(f"[FACTUAL GUARDRAIL] {alert_msg}")

        content.experiences = sanitized_experiences

        # -------------------------------------------------------------
        # 3. Guardrail de Habilidades (Skills)
        # -------------------------------------------------------------
        sanitized_skills: dict[str, list[str]] = {}
        for cat_name, skill_list in content.prioritized_skills.items():
            valid_skill_items: list[str] = []
            for item in skill_list:
                item_lower = item.strip().lower()
                # Coincidencia directa
                if item_lower in tech_universe or item_lower in ALLOWED_GENERIC_CONCEPTS:
                    valid_skill_items.append(item)
                    continue

                # Descomponer tokens del item
                item_tokens = [
                    t.strip() for t in re.split(r"[,/()&+\n:]+", item_lower) if len(t.strip()) >= 2
                ]

                # Si es un concepto genérico
                if any(concept in item_lower for concept in ALLOWED_GENERIC_CONCEPTS):
                    has_valid = any(
                        tok in tech_universe or tok in ALLOWED_GENERIC_CONCEPTS for tok in item_tokens
                    )
                    has_disallowed = any(
                        tok not in tech_universe and tok not in ALLOWED_GENERIC_CONCEPTS and len(tok) > 3
                        for tok in item_tokens
                    )
                    if has_valid and not has_disallowed:
                        valid_skill_items.append(item)
                        continue

                # Si todos o la mayoría de los tokens identificables están en el tech universe
                matching_tokens = [
                    tok for tok in item_tokens if tok in tech_universe or tok in ALLOWED_GENERIC_CONCEPTS
                ]
                disallowed_tokens = [
                    tok for tok in item_tokens if tok not in tech_universe and tok not in ALLOWED_GENERIC_CONCEPTS and len(tok) > 3
                ]

                if matching_tokens and not disallowed_tokens:
                    valid_skill_items.append(item)
                else:
                    alert_msg = f"Habilidad no comprobable purgada de skills: '{item}'"
                    alerts.append(alert_msg)
                    logger.warning(f"[FACTUAL GUARDRAIL] {alert_msg}")

            if valid_skill_items:
                sanitized_skills[cat_name] = valid_skill_items

        content.prioritized_skills = sanitized_skills

        return content, alerts
