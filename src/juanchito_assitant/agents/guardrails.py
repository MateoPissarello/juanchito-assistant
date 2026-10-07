import logging
from juanchito_assitant.agents.cv_writer import (
    TailoredExperience,
    TailoredInitiative,
    TailoredProject,
    TailoredResumeContent,
)
from juanchito_assitant.agents.matcher import MatchedContext

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
    "software architecture",
    "api design",
    "devops",
    "system design",
    "third-party api integrations",
    "webhook implementations",
    "webhooks",
    "infrastructure as code",
}


class FactualGuardrail:
    """Validador programático determinista para asegurar factualidad estricta y prevenir alucinaciones."""

    @classmethod
    def apply(
        cls,
        content: TailoredResumeContent,
        ctx: MatchedContext,
    ) -> tuple[TailoredResumeContent, list[str]]:
        """Aplica filtros deterministas a proyectos, experiencias y habilidades.

        Args:
            content: Objeto estructurado emitido por el WriterAgent.
            ctx: Contexto fáctico verificado del candidato desde SQLite.

        Returns:
            Tupla (contenido_saneado, alertas_de_guardrail).
        """
        alerts: list[str] = []

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
                sanitized_projects.append(p)
            else:
                alert_msg = f"Proyecto no existente purgado: '{p.name}'"
                alerts.append(alert_msg)
                logger.warning(f"[FACTUAL GUARDRAIL] {alert_msg}")

        content.projects = sanitized_projects

        # -------------------------------------------------------------
        # 2. Guardrail de Empresas e Iniciativas Laborales
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
                for init in exp.initiatives:
                    init_clean = init.name.strip().lower()
                    init_matched = None
                    for r_name, r_init in valid_init_names.items():
                        if r_name in init_clean or init_clean in r_name:
                            init_matched = r_init
                            break

                    if init_matched:
                        sanitized_inits.append(init)
                    else:
                        alert_msg = f"Iniciativa no verificable purgada: '{init.name}' en '{exp.company}'"
                        alerts.append(alert_msg)
                        logger.warning(f"[FACTUAL GUARDRAIL] {alert_msg}")

                # Si todas las iniciativas fueron purgadas pero la empresa es real, restaurar iniciativas verídicas
                if not sanitized_inits and real_inits_for_comp:
                    alerts.append(f"Restaurando iniciativas reales de SQLite para empresa '{exp.company}'")
                    for r in real_inits_for_comp:
                        sanitized_inits.append(
                            TailoredInitiative(name=r.project_name, bullets=r.bullets[:3])
                        )

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
        # Construir el conjunto de tecnologías comprobables del candidato
        tech_universe: set[str] = set()
        raw_tech_items: list[str] = []
        for cat in ctx.skills:
            raw_tech_items.extend(cat.skills)
        for w in ctx.work_matches:
            raw_tech_items.extend(w.technologies)
        for p in ctx.github_matches:
            raw_tech_items.extend(p.technologies)

        import re
        for raw in raw_tech_items:
            clean = raw.strip().lower()
            if not clean:
                continue
            tech_universe.add(clean)
            # Descomponer compuestas: "AWS (Lambda, Fargate, EKS)" -> "aws", "lambda", "fargate", "eks"
            tokens = [p.strip() for p in re.split(r"[,/()&+\n]+", clean) if len(p.strip()) >= 2]
            for tok in tokens:
                tech_universe.add(tok)

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
                    # Verificar que no contenga tecnologías mayores explícitamente ausentes
                    # Si contiene términos que están en tech_universe o generic concepts
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
