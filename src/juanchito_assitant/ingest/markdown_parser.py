import re
from pathlib import Path
from typing import Optional
from sqlmodel import Session, select, delete
from juanchito_assitant.models.profile import (
    PersonalInfo,
    WorkExperience,
    WorkProject,
    PersonalProject,
    Certification,
    Education,
    SkillCategory,
    AdditionalAchievement,
    FullProfile,
)

def clean_html(text: str) -> str:
    """Remueve tags HTML auxiliares de resume.lol (como <span class="spacer"></span>)."""
    return re.sub(r'<[^>]+>', '', text).strip()

def split_items_respecting_parens(text: str) -> list[str]:
    """Divide por comas pero sin romper expresiones entre paréntesis como AWS (Lambda, S3)."""
    items = []
    current = []
    paren_depth = 0
    for char in text:
        if char == '(':
            paren_depth += 1
            current.append(char)
        elif char == ')':
            paren_depth = max(0, paren_depth - 1)
            current.append(char)
        elif char == ',' and paren_depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(char)
    last_item = "".join(current).strip()
    if last_item:
        items.append(last_item)
    return items

def extract_technologies_from_bullets(bullets: list[str]) -> list[str]:
    """Extrae tecnologías y términos clave en **negrita** dentro de las viñetas."""
    techs = set()
    for b in bullets:
        matches = re.findall(r'\*\*([^*]+)\*\*', b)
        for m in matches:
            cleaned = m.strip()
            if len(cleaned) > 2 and not cleaned.isdigit() and not cleaned.endswith('%'):
                techs.add(cleaned)
    return sorted(list(techs))

def parse_resume_markdown(content: str) -> FullProfile:
    """
    Parsea un archivo Markdown de resume.lol y construye un objeto FullProfile
    con todas sus entidades estructuradas.
    """
    # 1. Variables de cabecera (@VAR=val1||val2)
    raw_vars = re.findall(r'^@([A-Z_]+)=\s*([^\n\r]+)', content, re.M)
    variables: dict[str, str] = {}
    for k, v in raw_vars:
        primary_val = v.split('||')[0].strip()
        variables[k] = primary_val

    # 2. Headline
    hl_match = re.search(r'<div class="headline">\s*(.*?)\s*</div>', content, re.S)
    headline = hl_match.group(1).strip() if hl_match else ""

    # 3. PersonalInfo
    personal = PersonalInfo(
        id=1,
        full_name=variables.get("NAME", "Mateo Pissarello"),
        timezone=variables.get("TZ", "GMT-05"),
        email=variables.get("EMAIL", "@EMAIL"),
        phone=variables.get("PHONE", "@PHONE"),
        linkedin=variables.get("LINKEDIN", "mateo-pissarello"),
        github=variables.get("GITHUB", "MateoPissarello"),
        headline=headline,
        extra_variables={k: v for k, v in variables.items() if k not in ["NAME", "TZ", "EMAIL", "PHONE", "LINKEDIN", "GITHUB"]}
    )

    # 4. Secciones Markdown (## Section)
    sections_raw = re.findall(r'^##\s+([^\n\r]+)\n(.*?)(?=\n##\s+|\Z)', content, re.M | re.S)
    sections = {title.strip(): body.strip() for title, body in sections_raw}

    # Profile Summary
    if "Profile" in sections:
        personal.profile_summary = sections["Profile"].strip()

    # Skills
    skills: list[SkillCategory] = []
    seen_categories = set()
    if "Skills" in sections:
        skill_lines = [l.strip() for l in sections["Skills"].split('\n') if l.strip().startswith('-')]
        for sl in skill_lines:
            match = re.match(r'^-\s+\*\*([^:]+):\*\*\s*(.*)$', sl)
            if match:
                cat_name = match.group(1).strip()
                # Si se repite "Languages", diferenciarlo como "Spoken Languages"
                if cat_name in seen_categories:
                    cat_name = f"Spoken {cat_name}" if "Native" in sl or "Spanish" in sl else f"{cat_name} (Additional)"
                seen_categories.add(cat_name)

                items = split_items_respecting_parens(match.group(2))
                skills.append(SkillCategory(category=cat_name, skills=items))

    # Experience & WorkProjects
    experiences: list[WorkExperience] = []
    if "Experience" in sections:
        exp_blocks = re.split(r'\n###\s+', '\n' + sections["Experience"])[1:]
        for idx, block in enumerate(exp_blocks, start=1):
            lines = [l.rstrip() for l in block.strip().split('\n') if l.strip()]
            if not lines:
                continue

            # Línea 1: Rol y Fechas
            role_line = lines[0]
            role_parts = re.split(r'<span[^>]*>', role_line)
            role = clean_html(role_parts[0]).strip()
            date_match = re.search(r'<span class="normal">\s*(.*?)\s*</span>', role_line)
            date_range = date_match.group(1).strip() if date_match else ""
            
            start_date, end_date = date_range, "Present"
            if '–' in date_range:
                parts = [p.strip() for p in date_range.split('–')]
                start_date, end_date = parts[0], parts[1]
            elif '-' in date_range:
                parts = [p.strip() for p in date_range.split('-')]
                start_date, end_date = parts[0], parts[1]

            # Línea 2: Empresa y Ubicación (#### Empresa <span...> Ubicacion)
            company, location = "", ""
            if len(lines) > 1 and lines[1].startswith('####'):
                comp_line = re.sub(r'^####\s*', '', lines[1])
                comp_parts = re.split(r'<span[^>]*>', comp_line)
                company = clean_html(comp_parts[0]).strip()
                location = clean_html(comp_parts[-1]).strip() if len(comp_parts) > 1 else ""

            exp = WorkExperience(
                role=role,
                company=company,
                location=location,
                start_date=start_date,
                end_date=end_date,
                is_current=("Present" in end_date.lower()),
                order_index=idx,
                projects=[]
            )

            # Extraer iniciativas técnicas (- **NombreIniciativa**)
            proj_blocks = re.split(r'\n-\s+\*\*', '\n' + '\n'.join(lines[2:]))[1:]
            for p_raw in proj_blocks:
                p_lines = p_raw.strip().split('\n')
                p_name = p_lines[0].replace('**', '').strip()
                bullets: list[str] = []
                for bl in p_lines[1:]:
                    bl_clean = re.sub(r'^\s*-\s*', '', bl).strip()
                    if bl_clean:
                        bullets.append(bl_clean)

                techs = extract_technologies_from_bullets(bullets)
                work_proj = WorkProject(
                    name=p_name,
                    bullets=bullets,
                    technologies=techs,
                    priority_weight=1
                )
                exp.projects.append(work_proj)

            experiences.append(exp)

    # Courses & Certifications
    certifications: list[Certification] = []
    if "Courses & Certifications" in sections:
        cert_groups = re.split(r'\n###\s+', '\n' + sections["Courses & Certifications"])[1:]
        for g in cert_groups:
            lines = [l.strip() for l in g.strip().split('\n') if l.strip()]
            if not lines:
                continue
            issuer = lines[0].strip()
            for cl in lines[1:]:
                if cl.startswith('####'):
                    c_clean = re.sub(r'^####\s*', '', cl)
                    date_match = re.search(r'<span class="normal">\s*(.*?)\s*</span>', c_clean)
                    issue_date = date_match.group(1).strip() if date_match else ""
                    title = clean_html(re.split(r'<span', c_clean)[0]).strip()
                    certifications.append(Certification(
                        issuer=issuer,
                        title=title,
                        issue_date=issue_date
                    ))

    # Education
    education_list: list[Education] = []
    if "Education" in sections:
        edu_blocks = re.split(r'\n###\s+', '\n' + sections["Education"])[1:]
        for ed in edu_blocks:
            lines = [l.strip() for l in ed.strip().split('\n') if l.strip()]
            if not lines:
                continue
            inst_clean = lines[0]
            date_match = re.search(r'<span class="normal">\s*(.*?)\s*</span>', inst_clean)
            date_range = date_match.group(1).strip() if date_match else ""
            institution = clean_html(re.split(r'<span', inst_clean)[0]).strip()

            degree, loc = "", ""
            if len(lines) > 1 and lines[1].startswith('####'):
                d_clean = re.sub(r'^####\s*', '', lines[1])
                parts = re.split(r'<span[^>]*>', d_clean)
                degree = clean_html(parts[0]).strip()
                loc = clean_html(parts[-1]).strip() if len(parts) > 1 else ""

            education_list.append(Education(
                institution=institution,
                degree=degree,
                date_range=date_range,
                location=loc
            ))

    # Additional
    additional_list: list[AdditionalAchievement] = []
    if "Additional" in sections:
        add_blocks = re.split(r'\n###\s+', '\n' + sections["Additional"])[1:]
        for ab in add_blocks:
            lines = [l.strip() for l in ab.strip().split('\n') if l.strip()]
            if not lines:
                continue
            cat_clean = lines[0]
            date_match = re.search(r'<span class="normal">\s*(.*?)\s*</span>', cat_clean)
            date_range = date_match.group(1).strip() if date_match else ""
            category_title = clean_html(re.split(r'<span', cat_clean)[0]).strip()

            inst, loc = "", ""
            if len(lines) > 1 and lines[1].startswith('####'):
                i_clean = re.sub(r'^####\s*', '', lines[1])
                parts = re.split(r'<span[^>]*>', i_clean)
                inst = clean_html(parts[0]).strip()
                loc = clean_html(parts[-1]).strip() if len(parts) > 1 else ""

            bullets: list[str] = []
            links: list[dict[str, str]] = []
            for al in lines[2:]:
                clean_bullet = re.sub(r'^\s*-\s*', '', al).strip()
                if clean_bullet:
                    found_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', clean_bullet)
                    for label, url in found_links:
                        links.append({"label": label.strip('{}'), "url": url})
                    bullets.append(clean_bullet)

            additional_list.append(AdditionalAchievement(
                category="Programming Contest",
                title=category_title,
                institution=inst,
                location=loc,
                date_range=date_range,
                description_bullets=bullets,
                links=links
            ))

    return FullProfile(
        personal=personal,
        experiences=experiences,
        personal_projects=[],
        certifications=certifications,
        education=education_list,
        skills=skills,
        additional_achievements=additional_list
    )

def seed_database_from_profile(profile: FullProfile, session: Session) -> None:
    """
    Puebla la base de datos SQLite con los datos del perfil de forma idempotente.
    """
    # 1. Personal Info (Upsert)
    existing_p = session.exec(select(PersonalInfo).where(PersonalInfo.id == 1)).first()
    if existing_p:
        existing_p.full_name = profile.personal.full_name
        existing_p.timezone = profile.personal.timezone
        existing_p.location = profile.personal.location
        existing_p.email = profile.personal.email
        existing_p.phone = profile.personal.phone
        existing_p.linkedin = profile.personal.linkedin
        existing_p.github = profile.personal.github
        existing_p.headline = profile.personal.headline
        existing_p.profile_summary = profile.personal.profile_summary
        existing_p.extra_variables = profile.personal.extra_variables
    else:
        session.add(profile.personal)

    # 2. Limpiar registros previos dependientes para evitar duplicación al re-sembrar
    session.exec(delete(WorkProject))
    session.exec(delete(WorkExperience))
    session.exec(delete(Certification))
    session.exec(delete(Education))
    session.exec(delete(SkillCategory))
    session.exec(delete(AdditionalAchievement))
    session.commit()

    # 3. Insertar Experiencias e Iniciativas
    for exp in profile.experiences:
        session.add(exp)
    
    # 4. Certificaciones, Educación, Skills y Additional
    for cert in profile.certifications:
        session.add(cert)
    for edu in profile.education:
        session.add(edu)
    for sk in profile.skills:
        session.add(sk)
    for ach in profile.additional_achievements:
        session.add(ach)

    session.commit()
