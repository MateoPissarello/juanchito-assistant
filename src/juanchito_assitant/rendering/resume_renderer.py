import re
from typing import Any
from juanchito_assitant.agents.matcher import MatchedContext, curate_project_technologies
from juanchito_assitant.models.profile import PersonalInfo


SECTION_HEADERS = {
    "en": {
        "profile": "## Profile",
        "skills": "## Skills",
        "experience": "## Experience",
        "projects": "## Projects",
        "courses": "## Courses & Certifications",
        "education": "## Education",
        "additional": "## Additional",
    },
    "es": {
        "profile": "## Perfil Profesional",
        "skills": "## Habilidades",
        "experience": "## Experiencia Laboral",
        "projects": "## Proyectos",
        "courses": "## Cursos y Certificaciones",
        "education": "## Educación",
        "additional": "## Logros Adicionales",
    },
}

MONTH_MAP_ES = [
    (r"\bJanuary\b", "Enero"),
    (r"\bFebruary\b", "Febrero"),
    (r"\bMarch\b", "Marzo"),
    (r"\bApril\b", "Abril"),
    (r"\bJune\b", "Junio"),
    (r"\bJuly\b", "Julio"),
    (r"\bAugust\b", "Agosto"),
    (r"\bSeptember\b", "Septiembre"),
    (r"\bOctober\b", "Octubre"),
    (r"\bNovember\b", "Noviembre"),
    (r"\bDecember\b", "Diciembre"),
    (r"\bJan\b", "Ene"),
    (r"\bApr\b", "Abr"),
    (r"\bAug\b", "Ago"),
    (r"\bDec\b", "Dic"),
]

SKILL_CATEGORY_MAP_ES = {
    "languages": "Lenguajes",
    "databases": "Bases de Datos",
    "data & ai": "Datos e IA",
    "data and ai": "Datos e IA",
    "cloud & devops": "Cloud y DevOps",
    "cloud and devops": "Cloud y DevOps",
    "other": "Otros",
    "others": "Otros",
    "spoken languages": "Idiomas",
    "backend": "Backend",
}

SKILL_ITEM_MAP_ES = {
    "microservices": "Microservicios",
    "event-driven architecture": "Arquitectura Orientada a Eventos",
    "distributed systems": "Sistemas Distribuidos",
    "clean architecture": "Arquitectura Limpia",
    "clean code": "Código Limpio",
    "spanish (native)": "Español (Nativo)",
    "english (professional working proficiency)": "Inglés (Competencia profesional)",
}

ROLE_MAP_ES = {
    "backend engineer": "Ingeniero Backend",
    "senior backend engineer": "Ingeniero Backend Senior",
    "junior backend engineer": "Ingeniero Backend",
    "backend developer": "Desarrollador Backend",
    "cloud engineer": "Ingeniero Cloud",
    "software engineer": "Ingeniero de Software",
    "ai engineer": "Ingeniero de IA",
    "full stack developer": "Desarrollador Full-Stack",
    "full-stack developer": "Desarrollador Full-Stack",
}

INITIATIVE_NAME_MAP_ES = {
    "zammad on kubernetes (eks)": "Zammad en Kubernetes (EKS)",
    "rag – hacienda a un click project (cali city hall)": "Proyecto RAG – Hacienda A Un Click (Alcaldía de Cali)",
    "repository management & migration dashboards": "Gestión de Repositorios y Dashboards de Migración",
}

KNOWN_ENGLISH_BULLETS_ES = {
    "accomplished a robust backend system for cinema operations by developing restful apis using **fastapi** and **sqlalchemy**.": (
        "Desarrollé un sistema backend robusto para operaciones de cine mediante la implementación de APIs RESTful con **FastAPI** y **SQLAlchemy**."
    ),
    "implemented secure authentication and authorization mechanisms with **oauth2** and **jwt**, ensuring data protection for user accounts and transactions.": (
        "Implementé mecanismos seguros de autenticación y autorización con **OAuth2** y **JWT**, garantizando la protección de datos en cuentas y transacciones."
    ),
    "streamlined deployment workflows and database migrations by integrating **docker** and **alembic**, facilitating consistent environments across development and production.": (
        "Optimicé los flujos de despliegue y migraciones de base de datos integrando **Docker** y **Alembic**, garantizando entornos consistentes entre desarrollo y producción."
    ),
    "created **aicodefixer**, a tool integrated with **sonarqube and github** that automatically fixes issues, generates new features, and builds unit tests using **generative ai**.": (
        "Desarrollé **AICodeFixer**, una herramienta integrada con **SonarQube y GitHub** que corrige incidencias automáticamente, genera nuevas funcionalidades y construye pruebas unitarias usando **IA Generativa**."
    ),
    "developed a workflow using **fastapi, keycloak, aws lambda, dynamodb, and llms (claudecode)** that transforms issues into natural language and generates automatic pull requests, reducing issue resolution time by **50%**.": (
        "Diseñé un flujo de trabajo con **FastAPI, Keycloak, AWS Lambda, DynamoDB y LLMs (ClaudeCode)** que transforma incidencias en lenguaje natural y genera Pull Requests automáticos, reduciendo el tiempo de resolución en un **50%**."
    ),
    "developed **aiforms**, an internal accelerator built with **docassemble (python)** and deployed on **aws fargate**, enabling the creation of dynamic forms in minutes.": (
        "Desarrollé **AIForms**, un acelerador interno construido con **Docassemble (Python)** y desplegado en **AWS Fargate**, permitiendo la creación de formularios dinámicos en minutos."
    ),
    "implemented **infrastructure as code** using **aws cdk (typescript)**, reducing deployment and maintenance times by **40%**.": (
        "Implementé **Infraestructura como Código (IaC)** utilizando **AWS CDK (TypeScript)**, reduciendo los tiempos de despliegue y mantenimiento en un **40%**."
    ),
    "designed a **repository monitoring and migration system** from **aws codecommit to github** using a **multi-account aws architecture**, integrating **eventbridge, lambda, ses, and dynamodb**.": (
        "Diseñé un **sistema de monitoreo y migración de repositorios** de **AWS CodeCommit a GitHub** bajo una **arquitectura AWS multi-cuenta**, integrando **EventBridge, Lambda, SES y DynamoDB**."
    ),
    "developed a **fastapi backend** connected to **dynamodb** and deployed on **aws fargate**, enabling centralized management of migration states and planning.": (
        "Desarrollé un **backend en FastAPI** conectado a **DynamoDB** y desplegado en **AWS Fargate**, habilitando la gestión centralizada de estados y planificación de migración."
    ),
    "led the **migration and redesign of the zammad platform** due to recurring failures and instability in the previous **aws ecs** deployment that impacted operational continuity.": (
        "Lideré la **migración y rediseño de la plataforma Zammad** eliminando fallos recurrentes e inestabilidad del despliegue previo en **AWS ECS** que impactaban la continuidad operativa."
    ),
    "designed and deployed a new **cloud-native, highly available architecture** on **amazon eks** using **aws cdk (typescript)**.": (
        "Diseñé y desplegué una **arquitectura cloud-native de alta disponibilidad** en **Amazon EKS** utilizando **AWS CDK (TypeScript)**."
    ),
    "implemented **argocd** for continuous deployment and declarative infrastructure management, improving traceability and change control.": (
        "Implementé **ArgoCD** para despliegue continuo y gestión declarativa de infraestructura, mejorando la trazabilidad y el control de cambios."
    ),
    "implemented a **retrieval-augmented generation (rag)** solution for the hacienda a un click project, playing a key role during the **business understanding phase**.": (
        "Implementé una solución **RAG (Retrieval-Augmented Generation)** para el proyecto Hacienda A Un Click, desempeñando un rol clave en la **fase de entendimiento de negocio**."
    ),
    "designed a solution that enabled the analysis and querying of more than **130 extensive documents**, including diagrams and procedural documentation across multiple departments, significantly accelerating the understanding of complex processes.": (
        "Diseñé una solución que permitió analizar y consultar más de **130 documentos extensos**, acelerando significativamente la comprensión de procesos complejos interdepartamentales."
    ),
    "led the **full backend migration** from **django rest framework** to **fastapi, postgresql, and sqlalchemy**, reducing api latency by **60%** and building more than **120 endpoints** in a serverless architecture.": (
        "Lideré la **migración completa del backend** de **Django REST Framework** a **FastAPI, PostgreSQL y SQLAlchemy**, reduciendo la latencia de la API en un **60%** y construyendo más de **120 endpoints** en una arquitectura serverless."
    ),
    "designed and implemented key features, including **20 database models with apis**, **10 react + typescript views**, and advanced modules such as **real-time chat (websockets + dynamodb)** and a **chatbot integrated with the openai api**.": (
        "Diseñé e implementé funcionalidades clave, incluyendo **20 modelos de base de datos con APIs**, **10 vistas en React + TypeScript** y módulos de **chat en tiempo real (WebSockets + DynamoDB)**."
    ),
}


class ResumeRenderer:
    """Renderizador determinista para documentos Markdown compatibles al 100% con resume.lol y resume.css."""

    @staticmethod
    def localize_date_es(date_str: str) -> str:
        """Traduce meses y marcadores temporales en inglés ('Jan.', 'Apr.', 'Dec.', 'Present') al español."""
        if not date_str:
            return date_str
        res = re.sub(r"\bPresent\b", "Presente", date_str, flags=re.IGNORECASE)
        res = re.sub(r"\bCurrent\b", "Actualidad", res, flags=re.IGNORECASE)
        for pattern, replacement in MONTH_MAP_ES:
            res = re.sub(pattern, replacement, res, flags=re.IGNORECASE)
        return res

    @staticmethod
    def localize_location_es(loc_str: str) -> str:
        """Traduce modalidades de ubicación ('Remote', 'On-site', 'Hybrid') al español."""
        if not loc_str:
            return loc_str
        res = re.sub(r"\bRemote\b", "Remoto", loc_str, flags=re.IGNORECASE)
        res = re.sub(r"\bOn-site\b", "Presencial", res, flags=re.IGNORECASE)
        res = re.sub(r"\bHybrid\b", "Híbrido", res, flags=re.IGNORECASE)
        return res

    @staticmethod
    def localize_role_es(role_str: str) -> str:
        if not role_str:
            return "Ingeniero de Software"
        mapped = ROLE_MAP_ES.get(role_str.strip().lower())
        return mapped if mapped else role_str

    @staticmethod
    def localize_initiative_name_es(name_str: str) -> str:
        if not name_str:
            return name_str
        mapped = INITIATIVE_NAME_MAP_ES.get(name_str.strip().lower())
        return mapped if mapped else name_str

    @staticmethod
    def localize_degree_es(degree_str: str) -> str:
        """Traduce los títulos académicos de Educación al español según el estándar acordado con Mateo."""
        if not degree_str:
            return degree_str
        d_low = degree_str.strip().lower()
        if "computer science" in d_low and "artificial intelligence" in d_low:
            return "Ingeniería en Ciencias de la Computación e Inteligencia Artificial"
        res = re.sub(
            r",\s*Software Development\s*/\s*Web\s*&\s*Backend Development",
            ", Desarrollo de Software / Desarrollo Web y Backend",
            degree_str,
            flags=re.IGNORECASE,
        )
        return res

    @staticmethod
    def localize_achievement_es(title: str, bullets: list[str]) -> tuple[str, list[str]]:
        """Traduce la sección de Logros Adicionales (Maratón de Programación) al español."""
        loc_title = title
        if title.strip().lower() in ("programming contest", "programming marathon"):
            loc_title = "Maratón de Programación"

        loc_bullets: list[str] = []
        for b in bullets:
            b_strip = b.strip()
            if "competing against more than" in b_strip.lower() and "spicy" in b_strip.lower():
                url_match = re.search(r"\]\((https?://[^)]+)\)", b_strip)
                url = (
                    url_match.group(1)
                    if url_match
                    else "https://www.usergioarboleda.edu.co/noticias/retos-talento-y-programacion-asi-fue-la-maraton-de-programacion-2024-2"
                )
                loc_bullets.append(
                    f"Participé en una [{{MARATON}}]({url}) compitiendo contra más de **25 equipos** de programas de ingeniería y matemáticas. Mi equipo **SPICY obtuvo el tercer puesto**."
                )
            else:
                loc_bullets.append(ResumeRenderer.localize_bullet_es(b_strip))
        return loc_title, loc_bullets

    @staticmethod
    def localize_bullet_es(bullet: str) -> str:
        """Garantiza que ninguna viñeta de fallback quede en inglés cuando el CV es en español."""
        b_clean = bullet.strip()
        b_low = b_clean.lower()
        if b_low in KNOWN_ENGLISH_BULLETS_ES:
            return KNOWN_ENGLISH_BULLETS_ES[b_low]

        # Si la viñeta comienza con un verbo en inglés típico de fallback de profile.db, traducir estructura base
        english_lead_patterns = [
            (r"^Accomplished a robust backend system for (.*?) by developing (.*?) using (.*)\.$", r"Desarrollé un sistema backend robusto para \1 mediante la implementación de \2 con \3."),
            (r"^Accomplished\b", "Logré"),
            (r"^Developed and implemented\b", "Desarrollé e implementé"),
            (r"^Developed\b", "Desarrollé"),
            (r"^Designed and implemented\b", "Diseñé e implementé"),
            (r"^Designed and provisioned\b", "Diseñé y aprovisioné"),
            (r"^Implemented\b", "Implementé"),
            (r"^Led the\b", "Lideré la"),
            (r"^Built\b", "Construí"),
            (r"^Automated\b", "Automaticé"),
            (r"^Migrated\b", "Migré"),
            (r"^Optimized\b", "Optimicé"),
            (r"^Configured\b", "Configuré"),
            (r"^Streamlined\b", "Optimicé"),
        ]
        res = b_clean
        for pat, rep in english_lead_patterns:
            res = re.sub(pat, rep, res)
        return res

    @staticmethod
    def render(
        headline: str,
        profile_summary: str,
        experiences: list[dict[str, Any]],
        skills: dict[str, list[str]],
        matched_ctx: MatchedContext,
        language: str = "en",
        projects: list[dict[str, Any]] | None = None,
    ) -> str:
        """Ensambla el documento final garantizando la estructura HTML y clases CSS exactas de resume.lol.

        Args:
            headline: Titular profesional adaptado a la vacante.
            profile_summary: Párrafo ejecutivo de perfil.
            experiences: Lista de empresas con sus roles, fechas, ubicación e iniciativas técnicas.
            skills: Diccionario ordenado {categoria: [skills]}.
            matched_ctx: Contexto con información de contacto, certificaciones, educación y proyectos.
            language: Idioma del documento ('en' o 'es').
            projects: Lista opcional de proyectos de software adaptados para renderizar en la sección de proyectos.

        Returns:
            Documento Markdown final con clases CSS y variables compatibles con resume.lol.
        """
        personal: PersonalInfo = matched_ctx.personal_info
        is_es = language.lower() == "es"
        headers = SECTION_HEADERS.get(language.lower(), SECTION_HEADERS["en"])
        maraton_var = "Maratón de Programación" if is_es else "Programming Contest"

        # 1. Variables de Cabecera
        lines: list[str] = [
            "<!--",
            "Welcome to resume.lol!",
            "",
            "Template based on Jake’s resume (LaTeX original).",
            "-->",
            "",
            "@REDACTED=false",
            f"@TZ= {personal.timezone or 'GMT-05'}",
            f"@NAME={personal.full_name}||Hidden Name",
            f"@EMAIL={personal.email}||contact@example.com",
            f"@PHONE={personal.phone}||123-456-fake",
            f"@LINKEDIN={personal.linkedin}||linkedin.com/in/fake",
            f"@GITHUB={personal.github}||fake",
            f"@MARATON={maraton_var}",
            "",
            "# {NAME}",
            "",
            '<div class="headline">',
            headline.strip(),
            "</div> ",
            '<div class="section headerInfo">',
            "",
            "- **{TZ}**",
            f"- {personal.location}",
            "- {PHONE}",
            "- [{EMAIL}](mailto:{EMAIL})",
            "- [linkedin.com/in/{LINKEDIN}](https://linkedin.com/in/{LINKEDIN})",
            "- [github.com/{GITHUB}](https://github.com/{GITHUB})",
            "",
            "</div>",
            "",
            "",
            headers["profile"],
            profile_summary.strip(),
            "",
            headers["skills"],
            "",
        ]

        # 2. Habilidades (Skills)
        for cat_name, skill_list in skills.items():
            if skill_list:
                disp_cat = SKILL_CATEGORY_MAP_ES.get(cat_name.strip().lower(), cat_name) if is_es else cat_name
                disp_skills = (
                    [SKILL_ITEM_MAP_ES.get(s.strip().lower(), s) for s in skill_list]
                    if is_es
                    else skill_list
                )
                lines.append(f"- **{disp_cat}:** {', '.join(disp_skills)}  ")
        lines.append("")

        # 3. Experiencia Laboral e Iniciativas
        lines.append(headers["experience"])
        lines.append("")

        for exp in experiences:
            role = exp.get("role", "Engineer")
            dates = exp.get("dates", "Present")
            company = exp.get("company", "Company")
            location = exp.get("location", "Remote")

            if is_es:
                role = ResumeRenderer.localize_role_es(role)
                dates = ResumeRenderer.localize_date_es(dates)
                location = ResumeRenderer.localize_location_es(location)

            lines.append(f'### {role} <span class="spacer"></span><span class="normal"> {dates} </span>')
            lines.append(f'#### {company} <span class="spacer"></span> {location}')
            lines.append("")

            for init in exp.get("initiatives", []):
                init_name = init.get("name", "Core Initiative")
                if is_es:
                    init_name = ResumeRenderer.localize_initiative_name_es(init_name)
                lines.append(f"- **{init_name}**")
                for bullet in init.get("bullets", []):
                    b_text = ResumeRenderer.localize_bullet_es(bullet) if is_es else bullet.strip()
                    # Viñeta anidada con 4 espacios de indentación
                    lines.append(f"    - {b_text}")
            lines.append("")

        # 4. Proyectos Técnicos Personales (GitHub) - Estilo 1 (resume.lol)
        target_projects = projects if projects is not None else [
            {
                "name": gm.name,
                "repo_url": gm.repo_url,
                "technologies": gm.technologies,
                "year": gm.year,
                "bullets": gm.bullets,
            }
            for gm in matched_ctx.github_matches
        ]

        if target_projects:
            lines.append(headers["projects"])
            lines.append("")
            for proj in target_projects:
                p_name = proj.get("name", "Personal Project")
                p_url = proj.get("repo_url")
                raw_techs = proj.get("technologies", [])
                if isinstance(raw_techs, list):
                    techs = curate_project_technologies(raw_techs, job=matched_ctx.target_job, max_techs=6)
                    tech_str = ", ".join(techs)
                else:
                    tech_str = str(raw_techs)
                year_str = proj.get("year", "")

                url_span = ""
                if p_url:
                    clean_display = p_url.replace("https://", "").replace("http://", "").rstrip("/")
                    url_span = f' <span class="spacer"></span><span class="normal"> [{clean_display}]({p_url}) </span>'

                lines.append(f"### {p_name}{url_span}")
                tech_line = f"#### {tech_str}"
                if year_str:
                    tech_line += f' <span class="spacer"></span> {year_str}'
                lines.append(tech_line)
                lines.append("")

                for b in proj.get("bullets", []):
                    b_text = ResumeRenderer.localize_bullet_es(b) if is_es else b.strip()
                    lines.append(f"- {b_text}")
                lines.append("")

        # 5. Cursos y Certificaciones (nombres oficiales de certificados, fechas localizadas si is_es)
        lines.append(headers["courses"])
        lines.append("")

        # Agrupar certificaciones por emisor
        certs_by_issuer: dict[str, list] = {}
        for c in matched_ctx.certifications[:6]:
            certs_by_issuer.setdefault(c.issuer, []).append(c)

        for issuer, cert_items in certs_by_issuer.items():
            lines.append(f"### {issuer}")
            for c in cert_items:
                c_date = ResumeRenderer.localize_date_es(c.issue_date) if (is_es and c.issue_date) else c.issue_date
                date_str = f' <span class="spacer"></span><span class="normal">{c_date}</span>' if c_date and c_date != "N/A" else ""
                lines.append(f"#### {c.title}{date_str}")
            lines.append("")

        # 6. Educación
        lines.append(headers["education"])
        lines.append("")
        for edu in matched_ctx.education:
            edu_date = ResumeRenderer.localize_date_es(edu.date_range) if (is_es and edu.date_range) else edu.date_range
            edu_degree = ResumeRenderer.localize_degree_es(edu.degree) if is_es else edu.degree
            edu_loc = ResumeRenderer.localize_location_es(edu.location) if is_es else edu.location
            date_str = f' <span class="spacer"></span><span class="normal">{edu_date}</span>' if edu_date else ""
            lines.append(f"### {edu.institution}{date_str}")
            lines.append(f'#### {edu_degree} <span class="spacer"></span> {edu_loc}')
            lines.append("")

        # 7. Proyectos Adicionales / Maratones
        if matched_ctx.achievements:
            lines.append(headers["additional"])
            lines.append("")
            for ach in matched_ctx.achievements:
                ach_date = ResumeRenderer.localize_date_es(ach.date_range) if (is_es and ach.date_range) else ach.date_range
                if is_es:
                    ach_title, ach_bullets = ResumeRenderer.localize_achievement_es(
                        ach.title, ach.description_bullets
                    )
                    ach_loc = ResumeRenderer.localize_location_es(ach.location) if ach.location else ach.location
                else:
                    ach_title = ach.title
                    ach_bullets = ach.description_bullets
                    ach_loc = ach.location
                date_str = f' <span class="spacer"></span><span class="normal"> {ach_date} </span>' if ach_date else ""
                lines.append(f"### {ach_title}{date_str}")
                inst_str = ach.institution or "Institution"
                loc_str = f" <span class=\"spacer\"></span> {ach_loc}" if ach_loc else ""
                lines.append(f"#### {inst_str}{loc_str}")
                lines.append("")
                for b in ach_bullets:
                    lines.append(f"- {b}")
            lines.append("")

        return "\n".join(lines).strip()
