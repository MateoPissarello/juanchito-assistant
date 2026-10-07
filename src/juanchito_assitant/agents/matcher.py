import re
from pydantic import BaseModel, Field
from sqlmodel import Session, select

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


def _normalize(term: str) -> str:
    return re.sub(r"[^\w\s]", "", term.lower()).strip()


COMMON_TECHS = {
    "aws", "gcp", "azure", "python", "java", "typescript", "javascript", "c++", "bash", "sql",
    "fastapi", "django", "flask", "react", "next.js", "vue", "spring boot", "express",
    "docker", "kubernetes", "k8s", "argocd", "terraform", "cdk", "cloudformation",
    "lambda", "fargate", "ecs", "eks", "s3", "dynamodb", "redis", "postgresql", "postgres",
    "elasticache", "eventbridge", "quicksight", "glue", "serverless", "microservices", "cloud-native",
    "rag", "llm", "llms", "bedrock", "openai", "claude", "claudecode", "gemini", "gpt",
    "agent", "agents", "agentic", "multi-agent", "langchain", "llamaindex", "embeddings",
    "vector", "vectors", "vector store", "generative ai", "genai", "machine learning", "ml",
    "deep learning", "dl", "nlp", "computer vision", "chatbot", "guardrails", "llmops",
    "oop", "solid", "rest", "apis", "api", "graphql", "websockets", "sse", "web scraping",
    "playwright", "selenium", "scrapy", "ci/cd", "kafka", "snowflake", "rust"
}

TECHNICAL_SYNONYMS = {
    "rag": [
        "retrieval-augmented generation", "retrieval augmented generation",
        "vector search", "vector store", "s3 vectors", "bedrock",
        "embeddings", "similarity search", "retrieval systems",
        "retrieval pipelines", "retrieval",
    ],
    "llm": [
        "llms", "large language model", "large language models",
        "generative ai", "genai", "claude", "claudecode", "gemini",
        "openai", "gpt",
    ],
    "llms": [
        "llm", "large language model", "large language models",
        "generative ai", "genai", "claude", "claudecode", "gemini",
        "openai", "gpt",
    ],
    "agent": [
        "agents", "agentic", "multi-agent", "multi agent",
        "agent frameworks", "agent orchestration", "agent execution",
        "tool use", "tool-using", "agentic-ai", "agent definition",
        "multi-agent system", "multi-agent systems",
    ],
    "agentic": [
        "agents", "agent", "multi-agent", "multi agent",
        "agent frameworks", "agent orchestration", "agent execution", "agentic-ai",
    ],
    "multi-agent": [
        "agent", "agents", "agentic", "agent orchestration",
        "multi-agent orchestration", "multi agent", "multi-agent system",
        "multi-agent systems",
    ],
    "ai": [
        "artificial intelligence", "generative ai", "genai",
        "machine learning", "deep learning", "llm", "llms", "agentic",
    ],
    "iac": [
        "infrastructure as code", "cdk", "terraform", "cloudformation", "aws cdk",
    ],
    "infrastructure as code": [
        "iac", "cdk", "terraform", "cloudformation", "aws cdk",
    ],
    "aws": [
        "amazon web services", "lambda", "fargate", "eks", "ecs",
        "bedrock", "dynamodb", "s3", "cloudwatch", "elasticache",
        "ses", "eventbridge", "quicksight", "glue",
    ],
    "kubernetes": [
        "k8s", "eks", "argocd", "helm", "kubectl",
    ],
    "api": [
        "apis", "rest", "restful", "fastapi", "graphql", "http apis", "endpoints",
    ],
    "apis": [
        "api", "rest", "restful", "fastapi", "graphql", "http apis", "endpoints",
    ],
    "rest": [
        "api", "apis", "restful", "fastapi", "http apis", "endpoints",
    ],
    "oop": [
        "object-oriented", "object oriented", "design patterns", "solid",
        "solid principles", "strategy pattern",
    ],
    "solid": [
        "solid principles", "oop", "design patterns", "strategy pattern",
    ],
    "cloud-native": [
        "cloud native", "serverless", "microservices", "kubernetes", "eks", "fargate",
    ],
    "guardrails": [
        "guardrail", "safety", "governance", "compliance", "evaluation",
    ],
    "llmops": [
        "evaluation harnesses", "model evaluation", "model monitoring",
        "model registry", "drift detection", "prompt monitoring", "eval infrastructure",
    ],
    "scraping": [
        "web scraping", "crawler", "crawling", "playwright", "selenium", "scrapy",
    ],
    "devops": [
        "ci/cd", "continuous integration", "github actions", "docker", "argocd",
    ],
}

STOP_PREFIXES = [
    "experience with ", "experience in ", "experience of ", "experience implementing ",
    "experience designing ", "experience operating ", "experience evaluating ",
    "production ", "strong ", "familiarity with ", "understanding of ", "knowledge of ",
    "design and operation of ", "design and consumption of ", "orchestration of ",
    "proficiency in ", "ability to ",
]

STOP_SUFFIXES = [
    " experience", " practices", " practice", " skills", " skill", " development",
    " frameworks", " framework", " systems", " system", " platforms", " platform",
]


def extract_key_terms(raw_list: list[str]) -> list[str]:
    """Extrae conceptos y tecnologías atómicas a partir de frases de requisitos."""
    found = set()
    for raw in raw_list:
        raw_strip = raw.strip()
        if not raw_strip:
            continue

        # 1. Si ya es un término corto (1 a 2 palabras) sin prefijo de parada
        if len(raw_strip.split()) <= 2 and not any(raw_strip.lower().startswith(p) for p in STOP_PREFIXES):
            clean_tok = re.sub(r"^[^\w]+|[^\w]+$", "", raw_strip)
            if len(clean_tok) >= 2:
                found.add(clean_tok)

        # 2. Términos entre paréntesis (ej. (CDK, CloudFormation, or Terraform))
        for pm in re.findall(r"\((.*?)\)", raw_strip):
            for sub in re.split(r"[,;/+]|\bor\b|\band\b", pm):
                sub_clean = re.sub(r"^[^\w]+|[^\w]+$", "", sub.strip())
                if len(sub_clean) >= 2:
                    found.add(sub_clean)

        # 3. Remover paréntesis y descomponer chunks
        no_parens = re.sub(r"\(.*?\)", "", raw_strip)
        chunks = re.split(r"[,;:\n]|\bor\b|\band\b", no_parens)
        for chunk in chunks:
            c = chunk.strip()
            c_low = c.lower()
            for p in STOP_PREFIXES:
                if c_low.startswith(p):
                    c = c[len(p):].strip()
                    c_low = c.lower()
            for s in STOP_SUFFIXES:
                if c_low.endswith(s):
                    c = c[:-len(s)].strip()
                    c_low = c.lower()
            if 2 <= len(c) <= 35 and len(c.split()) <= 4:
                found.add(c)

        # 4. Escanear tokens conocidos o frases específicas
        raw_lower = raw_strip.lower().replace("/", " ").replace("(", " ").replace(")", " ").replace(",", " ")
        for token in re.split(r"[\s;:,\-\+]+", raw_lower):
            t = token.strip()
            if t in COMMON_TECHS or (t.isupper() and len(t) >= 2):
                found.add(t)
        if "infrastructure as code" in raw_lower:
            found.add("infrastructure as code")
        if "multi-agent" in raw_strip.lower() or "multi agent" in raw_lower:
            found.add("multi-agent")
        if "agentic" in raw_lower:
            found.add("agentic")
        if "retrieval" in raw_lower or "rag" in raw_lower:
            found.add("rag")
        if "guardrail" in raw_lower:
            found.add("guardrails")
    return sorted(set(t.lower() for t in found if t.strip()))


def matches_term(term: str, corpus_lower: str, techs_set_lower: set[str]) -> bool:
    """Valida coincidencia técnica usando tokens en techs_set, regex word boundaries y alias."""
    t_low = term.lower()
    if t_low in techs_set_lower or any(t_low == tech or t_low in tech.split() for tech in techs_set_lower):
        return True
    pattern = r"\b" + re.escape(t_low) + r"\b"
    if re.search(pattern, corpus_lower):
        return True
    synonyms = TECHNICAL_SYNONYMS.get(t_low, [])
    for syn in synonyms:
        if syn in techs_set_lower:
            return True
        syn_pattern = r"\b" + re.escape(syn) + r"\b"
        if re.search(syn_pattern, corpus_lower):
            return True
    return False


def _score_text_and_techs(
    techs: list[str],
    text_corpus: str,
    must_terms: list[str],
    nice_terms: list[str],
    ats_terms: list[str],
    is_ai_role: bool = False,
    is_cloud_devops_role: bool = False,
) -> tuple[float, list[str]]:
    """Calcula el puntaje de afinidad y retorna las tecnologías que hicieron match."""
    score = 0.0
    matched_skills: set[str] = set()

    corpus_lower = text_corpus.lower()
    techs_set_lower = {t.lower() for t in techs}

    for must in must_terms:
        if matches_term(must, corpus_lower, techs_set_lower):
            score += 3.0
            matched_skills.add(must)

    for nice in nice_terms:
        if matches_term(nice, corpus_lower, techs_set_lower):
            score += 1.5
            matched_skills.add(nice)

    for kw in ats_terms:
        if matches_term(kw, corpus_lower, techs_set_lower):
            score += 1.0
            matched_skills.add(kw)

    # Bonificación de alineación de dominio técnico
    if is_ai_role:
        ai_hits = any(
            matches_term(k, corpus_lower, techs_set_lower)
            for k in [
                "rag", "llm", "agent", "generative ai", "bedrock",
                "vector", "openai", "claudecode", "nlp", "machine learning",
            ]
        )
        if ai_hits:
            score += 6.0
            matched_skills.add("role:ai_alignment")

    if is_cloud_devops_role:
        cloud_hits = any(
            matches_term(k, corpus_lower, techs_set_lower)
            for k in [
                "kubernetes", "eks", "argocd", "terraform", "iac",
                "infrastructure as code", "cdk", "fargate",
            ]
        )
        if cloud_hits:
            score += 6.0
            matched_skills.add("role:cloud_devops_alignment")

    return score, sorted(matched_skills)


class WorkProjectMatch(BaseModel):
    company: str
    role: str
    dates: str
    location: str
    project_name: str
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    match_score: float = 0.0
    matching_skills: list[str] = Field(default_factory=list)


class PersonalProjectMatch(BaseModel):
    name: str
    repo_url: str | None = None
    description: str | None = None
    category: str | None = None
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    match_score: float = 0.0
    matching_skills: list[str] = Field(default_factory=list)
    year: str = "2024"


class MatchedContext(BaseModel):
    personal_info: PersonalInfo
    work_matches: list[WorkProjectMatch] = Field(default_factory=list)
    github_matches: list[PersonalProjectMatch] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    skills: list[SkillCategory] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    achievements: list[AdditionalAchievement] = Field(default_factory=list)
    target_job: JobRequirements


class MatcherAgent:
    """Agente para cruzar los requisitos del empleo contra los activos de profile.db."""

    def __init__(self, session: Session):
        self.session = session

    def match(
        self,
        job: JobRequirements,
        max_work_projects: int = 4,
        max_github_projects: int = 2,
    ) -> MatchedContext:
        """Puntúa y selecciona los activos más relevantes para la vacante."""
        # 1. Información Personal
        personal = self.session.exec(select(PersonalInfo)).first() or PersonalInfo()

        # 2. Análisis del Dominio Objetivo (guiado primordialmente por job_title)
        job_title_low = (job.job_title or "").lower()
        role_summary_low = (job.role_summary or "").lower()
        is_ai_role = any(
            k in job_title_low
            for k in ["ai", "artificial intelligence", "machine learning", "ml", "llm", "generative", "agentic", "nlp", "computer vision"]
        ) or (
            not any(k in job_title_low for k in ["backend", "frontend", "devops", "cloud"])
            and any(k in role_summary_low for k in ["artificial intelligence", "agentic ai", "generative ai", "large language model", "llm services"])
        )
        is_cloud_devops_role = any(
            k in job_title_low
            for k in ["cloud", "devops", "platform engineer", "sre", "infrastructure", "kubernetes", "site reliability"]
        ) and not is_ai_role

        must_terms = extract_key_terms(job.must_have_skills)
        nice_terms = extract_key_terms(job.nice_to_have_skills)
        ats_terms = extract_key_terms(job.ats_keywords)

        # Mapa de categorías de TrackedRepo para proyectos personales
        tracked_map = {t.name: (t.category or "") for t in self.session.exec(select(TrackedRepo)).all()}

        # 3. Experiencia Laboral e Iniciativas
        experiences = self.session.exec(select(WorkExperience).order_by(WorkExperience.order_index)).all()
        scored_work_projects: list[WorkProjectMatch] = []

        for exp in experiences:
            date_str = f"{exp.start_date} – {exp.end_date}"
            for proj in exp.projects:
                text_corpus = f"{proj.name} {' '.join(proj.bullets)} {' '.join(proj.technologies)}"
                score, matched_skills = _score_text_and_techs(
                    techs=proj.technologies,
                    text_corpus=text_corpus,
                    must_terms=must_terms,
                    nice_terms=nice_terms,
                    ats_terms=ats_terms,
                    is_ai_role=is_ai_role,
                    is_cloud_devops_role=is_cloud_devops_role,
                )
                scored_work_projects.append(
                    WorkProjectMatch(
                        company=exp.company,
                        role=exp.role,
                        dates=date_str,
                        location=exp.location,
                        project_name=proj.name,
                        bullets=proj.bullets,
                        technologies=proj.technologies,
                        match_score=score,
                        matching_skills=matched_skills,
                    )
                )

        scored_work_projects.sort(key=lambda x: x.match_score, reverse=True)

        # Habilidades cubiertas por la experiencia laboral
        work_covered_skills: set[str] = set()
        for wp in scored_work_projects:
            work_covered_skills.update(wp.matching_skills)

        # 4. Proyectos Personales / Repositorios GitHub
        github_repos = self.session.exec(select(PersonalProject)).all()
        scored_repos: list[PersonalProjectMatch] = []

        for repo in github_repos:
            repo_cat = tracked_map.get(repo.name, "")
            text_corpus = f"{repo.name} {repo_cat} {repo.description or ''} {' '.join(repo.bullets)} {' '.join(repo.technologies)}"
            techs_with_cat = list(repo.technologies)
            if repo_cat:
                techs_with_cat.append(repo_cat)

            score, matched_skills = _score_text_and_techs(
                techs=techs_with_cat,
                text_corpus=text_corpus,
                must_terms=must_terms,
                nice_terms=nice_terms,
                ats_terms=ats_terms,
                is_ai_role=is_ai_role,
                is_cloud_devops_role=is_cloud_devops_role,
            )

            # Boost si la categoría técnica del repositorio coincide con el cargo
            cat_low = repo_cat.lower()
            if is_ai_role and any(k in cat_low for k in ["ai", "multi-agent", "nlp", "ml"]):
                score += 5.0
                matched_skills.append("role:ai_category")
            elif is_cloud_devops_role and any(k in cat_low for k in ["cloud", "devops", "terraform"]):
                score += 5.0
                matched_skills.append("role:cloud_category")

            year_val = repo.last_pushed_at[:4] if (repo.last_pushed_at and len(repo.last_pushed_at) >= 4) else "2024"
            scored_repos.append(
                PersonalProjectMatch(
                    name=repo.name,
                    repo_url=repo.repo_url or f"https://github.com/{personal.github}/{repo.name}",
                    description=repo.description,
                    category=repo_cat or None,
                    bullets=repo.bullets,
                    technologies=repo.technologies,
                    match_score=score,
                    matching_skills=matched_skills,
                    year=year_val,
                )
            )

        scored_repos.sort(key=lambda x: x.match_score, reverse=True)

        # Filtrar repositorios con afinidad real (score >= 4.0 o que aporten skills no cubiertas)
        relevant_repos = [
            r for r in scored_repos
            if r.match_score >= 4.0 or (r.match_score > 0 and not set(r.matching_skills).issubset(work_covered_skills))
        ]
        selected_github = relevant_repos[:max_github_projects]

        # 5. Asignación Dinámica de Presupuesto
        # Si hay repositorios seleccionados, asignamos 3 iniciativas laborales; si no, 4
        if len(selected_github) >= 1:
            budget_work = 3
        else:
            budget_work = max_work_projects

        # 6. Selección Inteligente de Iniciativas Laborales
        selected_work: list[WorkProjectMatch] = []
        companies_seen: set[str] = set()
        top_score = scored_work_projects[0].match_score if scored_work_projects else 0.0
        high_threshold = max(4.0, top_score * 0.5)

        # Pase 1: Iniciativas de alta afinidad técnica en orden de puntuación
        for wp in scored_work_projects:
            if wp.match_score >= high_threshold and len(selected_work) < budget_work:
                selected_work.append(wp)
                companies_seen.add(wp.company)

        # Pase 2: Garantizar representación de empresas con score positivo no vistas
        for wp in scored_work_projects:
            if wp.company not in companies_seen and wp.match_score > 0 and len(selected_work) < budget_work:
                selected_work.append(wp)
                companies_seen.add(wp.company)

        # Pase 3: Rellenar cupo restante con los mejores proyectos disponibles
        for wp in scored_work_projects:
            if wp not in selected_work and len(selected_work) < budget_work:
                selected_work.append(wp)

        # 7. Certificaciones
        certs = self.session.exec(select(Certification)).all()
        def cert_relevance(c: Certification) -> int:
            t = f"{c.issuer} {c.title}".lower()
            return sum(2 for m in must_terms if m.lower() in t) + sum(1 for n in nice_terms if n.lower() in t)

        certs.sort(key=cert_relevance, reverse=True)

        # 8. Habilidades (Ordenar categorías según relevancia para el rol)
        categories = self.session.exec(select(SkillCategory)).all()
        def category_score(cat: SkillCategory) -> int:
            skills_str = " ".join(cat.skills).lower()
            return sum(3 for m in must_terms if m.lower() in skills_str) + sum(1 for n in nice_terms if n.lower() in skills_str)

        categories.sort(key=category_score, reverse=True)

        # 9. Educación y Logros Adicionales
        education = self.session.exec(select(Education)).all()
        achievements = self.session.exec(select(AdditionalAchievement)).all()

        return MatchedContext(
            personal_info=personal,
            work_matches=selected_work,
            github_matches=selected_github,
            certifications=certs,
            skills=categories,
            education=education,
            achievements=achievements,
            target_job=job,
        )
