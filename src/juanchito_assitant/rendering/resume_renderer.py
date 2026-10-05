from typing import Any
from juanchito_assitant.agents.matcher import MatchedContext
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



class ResumeRenderer:
    """Renderizador determinista para documentos Markdown compatibles al 100% con resume.lol y resume.css."""

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
        headers = SECTION_HEADERS.get(language.lower(), SECTION_HEADERS["en"])


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
            "@MARATON=Programming Contest",
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
                lines.append(f"- **{cat_name}:** {', '.join(skill_list)}  ")
        lines.append("")

        # 3. Experiencia Laboral e Iniciativas
        lines.append(headers["experience"])
        lines.append("")

        for exp in experiences:
            role = exp.get("role", "Engineer")
            dates = exp.get("dates", "Present")
            company = exp.get("company", "Company")
            location = exp.get("location", "Remote")

            if language.lower() == "es":
                dates = dates.replace("Present", "Presente")
                location = location.replace("Remote", "Remoto")

            lines.append(f'### {role} <span class="spacer"></span><span class="normal"> {dates} </span>')
            lines.append(f'#### {company} <span class="spacer"></span> {location}')
            lines.append("")

            for init in exp.get("initiatives", []):
                init_name = init.get("name", "Core Initiative")
                lines.append(f"- **{init_name}**")
                for bullet in init.get("bullets", []):
                    # Viñeta anidada con 4 espacios de indentación
                    lines.append(f"    - {bullet.strip()}")
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
                techs = proj.get("technologies", [])
                tech_str = ", ".join(techs) if isinstance(techs, list) else str(techs)
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
                    lines.append(f"- {b.strip()}")
                lines.append("")

        # 5. Cursos y Certificaciones
        lines.append(headers["courses"])
        lines.append("")

        # Agrupar certificaciones por emisor
        certs_by_issuer: dict[str, list] = {}
        for c in matched_ctx.certifications[:6]:
            certs_by_issuer.setdefault(c.issuer, []).append(c)

        for issuer, cert_items in certs_by_issuer.items():
            lines.append(f"### {issuer}")
            for c in cert_items:
                date_str = f' <span class="spacer"></span><span class="normal">{c.issue_date}</span>' if c.issue_date and c.issue_date != "N/A" else ""
                lines.append(f"#### {c.title}{date_str}")
            lines.append("")

        # 6. Educación
        lines.append(headers["education"])
        lines.append("")
        for edu in matched_ctx.education:
            date_str = f' <span class="spacer"></span><span class="normal">{edu.date_range}</span>' if edu.date_range else ""
            lines.append(f"### {edu.institution}{date_str}")
            lines.append(f'#### {edu.degree} <span class="spacer"></span> {edu.location}')
            lines.append("")

        # 7. Proyectos Adicionales / Maratones
        if matched_ctx.achievements:
            lines.append(headers["additional"])
            lines.append("")
            for ach in matched_ctx.achievements:
                date_str = f' <span class="spacer"></span><span class="normal"> {ach.date_range} </span>' if ach.date_range else ""
                lines.append(f"### {ach.title}{date_str}")
                inst_str = ach.institution or "Institution"
                loc_str = f" <span class=\"spacer\"></span> {ach.location}" if ach.location else ""
                lines.append(f"#### {inst_str}{loc_str}")
                lines.append("")
                for b in ach.description_bullets:
                    lines.append(f"- {b}")
            lines.append("")

        return "\n".join(lines).strip()
