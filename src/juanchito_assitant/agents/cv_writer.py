import json
import logging
import re
import httpx
from pydantic import BaseModel, Field

from juanchito_assitant.agents.matcher import MatchedContext, curate_project_technologies
from juanchito_assitant.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MODELS_CV_WRITER,
    MODEL_CV_WRITER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
from juanchito_assitant.agents.llm_client import call_openrouter
from juanchito_assitant.rendering.resume_renderer import ResumeRenderer

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)


class TailoredInitiative(BaseModel):
    name: str = Field(description="Nombre de la iniciativa técnica.")
    bullets: list[str] = Field(description="2 a 4 viñetas Google XYZ con métricas y tecnologías en negrita (**tech**, **metric**).")


class TailoredExperience(BaseModel):
    company: str
    role: str
    dates: str
    location: str
    initiatives: list[TailoredInitiative] = Field(default_factory=list)


class TailoredProject(BaseModel):
    name: str = Field(description="Nombre del proyecto técnico / repositorio.")
    repo_url: str | None = Field(default=None, description="URL del repositorio en GitHub.")
    technologies: list[str] = Field(default_factory=list, description="Lista de 3 a 6 tecnologías clave utilizadas.")
    year: str = Field(default="2024", description="Año de desarrollo o última actualización.")
    bullets: list[str] = Field(description="1 a 3 viñetas Google XYZ con métricas y tecnologías en negrita (**tech**, **metric**).")


class TailoredResumeContent(BaseModel):
    headline: str = Field(description="Titular profesional adaptado a la vacante.")
    profile_summary: str = Field(description="1 párrafo conciso enfocado en el match con el rol.")
    experiences: list[TailoredExperience] = Field(default_factory=list)
    projects: list[TailoredProject] = Field(
        default_factory=list,
        description="Proyectos técnicos de software personales (GitHub) seleccionados y adaptados para la vacante.",
    )
    prioritized_skills: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Categorías de skills y sus listas de habilidades ordenadas por relevancia para el rol.",
    )


class WriterAgent:
    """Agente para redactar y adaptar el CV en formato Markdown de resume.lol con soporte HTML/CSS nativo."""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | list[str] | None = None,
        client=None,
        http_transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 60.0,
    ):
        self.http_transport = http_transport
        self.timeout = timeout

        if provider:
            self.provider = provider.lower()
        elif OPENROUTER_API_KEY:
            self.provider = "openrouter"
        elif GEMINI_API_KEY or client is not None:
            self.provider = "gemini"
        else:
            self.provider = "none"

        if self.provider == "openrouter":
            self.api_key = api_key or OPENROUTER_API_KEY
            self.model = model or MODELS_CV_WRITER
            self.gemini_client = None
        elif self.provider == "gemini":
            self.api_key = api_key or GEMINI_API_KEY
            self.model = model or GEMINI_MODEL
            if client:
                self.gemini_client = client
            elif self.api_key and genai:
                self.gemini_client = genai.Client(api_key=self.api_key)
            else:
                self.gemini_client = None
        else:
            self.api_key = api_key or ""
            self.model = model or ""
            self.gemini_client = None

        self.last_guardrail_alerts: list[str] = []

    def _build_context_prompt(
        self,
        ctx: MatchedContext,
        feedback: list[str] | None = None,
        previous_draft: str | None = None,
    ) -> str:
        from juanchito_assitant.agents.guardrails import FactualGuardrail

        owned_job_skills, unowned_job_skills = FactualGuardrail.classify_job_skills(ctx.target_job, ctx)

        work_str = ""
        companies: dict[str, list] = {}
        for w in ctx.work_matches:
            companies.setdefault(w.company, []).append(w)

        for comp, projs in companies.items():
            first = projs[0]
            work_str += f"\nCompany: {comp} | Role: {first.role} | Dates: {first.dates} | Location: {first.location}\n"
            for p in projs:
                work_str += f"  Initiative: {p.project_name}\n"
                work_str += f"  Techs: {', '.join(p.technologies)}\n"
                if p.match_reason:
                    work_str += f"  Selection Reason / Angle to Highlight: {p.match_reason}\n"
                for b in p.bullets:
                    work_str += f"  - {b}\n"

        skills_dict: dict[str, list[str]] = {cat.category: cat.skills for cat in ctx.skills[:5]}

        projects_str = ""
        if ctx.github_matches:
            projects_str += "Available Technical Projects (GitHub):\n"
            for p in ctx.github_matches:
                projects_str += f"- Project Name: {p.name}\n"
                if p.category:
                    projects_str += f"  Category: {p.category}\n"
                if p.repo_url:
                    projects_str += f"  Repo URL: {p.repo_url}\n"
                projects_str += f"  Year: {p.year}\n"
                curated_p_techs = curate_project_technologies(p.technologies, job=ctx.target_job, max_techs=6)
                projects_str += f"  Relevant Core Techs (select 3 to 6 from these): {', '.join(curated_p_techs)}\n"
                if p.match_reason:
                    projects_str += f"  Selection Reason / Angle to Highlight: {p.match_reason}\n"
                if p.description:
                    projects_str += f"  Description: {p.description}\n"
                if p.bullets:
                    projects_str += "  Key achievements / bullets:\n"
                    for b in p.bullets:
                        projects_str += f"    * {b}\n"

        skill_boundary_section = (
            "\n--- DETERMINISTIC SKILL BOUNDARY ANALYSIS ---\n"
            f"- VERIFIED JOB SKILLS OWNED BY CANDIDATE (MUST INCLUDE IN RESUME): {', '.join(owned_job_skills) if owned_job_skills else 'Use candidate skills from profile'}\n"
            f"- UNOWNED JOB SKILLS (CANDIDATE DOES NOT HAVE THESE - STRICTLY FORBIDDEN TO MENTION OR FABRICATE): {', '.join(unowned_job_skills) if unowned_job_skills else 'None'}\n"
            "---------------------------------------------\n"
        )

        feedback_section = ""
        if feedback:
            feedback_section = (
                "\n\n--- CRITICAL EVALUATOR FEEDBACK (MUST FIX IN THIS REVISION) ---\n"
                + "\n".join(f"- {f}" for f in feedback)
                + "\n---------------------------------------------------------------\n"
            )

        previous_draft_section = ""
        if previous_draft:
            previous_draft_section = (
                "\n\n--- PREVIOUS RESUME DRAFT (SURGICAL REVISION MODE) ---\n"
                "Below is the draft you generated in the previous iteration. "
                "Do NOT rewrite from scratch blindly: preserve the strong bullets and already-matched keywords, "
                "and apply targeted refinements specifically to resolve the CRITICAL EVALUATOR FEEDBACK above.\n"
                f"{previous_draft}\n"
                "------------------------------------------------------\n"
            )

        job = ctx.target_job
        return (
            f"TARGET JOB TITLE: {job.job_title}\n"
            f"TARGET COMPANY: {job.company_name or 'Hiring Company'}\n"
            f"SENIORITY LEVEL: {job.seniority_level or 'Mid-Senior'}\n"
            f"MUST-HAVE SKILLS: {', '.join(job.must_have_skills)}\n"
            f"NICE-TO-HAVE SKILLS: {', '.join(job.nice_to_have_skills)}\n"
            f"ATS KEYWORDS: {', '.join(job.ats_keywords)}\n"
            f"ROLE SUMMARY: {job.role_summary}\n"
            f"{skill_boundary_section}"
            f"{feedback_section}"
            f"{previous_draft_section}\n"
            f"--- CANDIDATE MASTER PROFILE (FACTUAL TRUTH - DO NOT INVENT) ---\n"
            f"Personal: {ctx.personal_info.full_name} | {ctx.personal_info.location}\n"
            f"Available Skills:\n{json.dumps(skills_dict, indent=2)}\n"
            f"Available Work Initiatives:\n{work_str}\n"
            f"{projects_str}\n"
        )

    async def write_resume(
        self,
        ctx: MatchedContext,
        feedback: list[str] | None = None,
        language: str = "en",
        previous_draft: str | None = None,
    ) -> str:
        """Genera el contenido estructurado adaptado con LLM y lo renderiza con ResumeRenderer."""
        user_prompt = self._build_context_prompt(ctx, feedback=feedback, previous_draft=previous_draft)
        schema_json = json.dumps(TailoredResumeContent.model_json_schema())

        if language.lower() == "es":
            lang_instruction = (
                "LANGUAGE DIRECTIVE (CRITICAL - 100% SPANISH OUTPUT):\n"
                "You MUST generate ALL output fields in professional Spanish (español profesional técnico para ingeniería de software):\n"
                "- `headline` in Spanish (e.g., 'Ingeniero Backend Senior | Arquitectura Cloud & Microservicios').\n"
                "- `profile_summary` in 1 powerful paragraph in Spanish (~60-80 words) highlighting backend, cloud, and distributed systems.\n"
                "- In `experiences`, translate `role` (e.g., 'Ingeniero Backend', 'Desarrollador Backend', 'Ingeniero Cloud'), `dates` (e.g., 'Ene. 2026 – Mar. 2026', 'Presente'), and `location` (e.g., 'Remoto', 'Bogotá, Colombia (Presencial)') to Spanish.\n"
                "- For each initiative in `experiences`, reformulate 2 to 4 bullets following the Google XYZ formula in Spanish: Logré [X] medido por [Y] mediante [Z], using strong action verbs in past tense (e.g., 'Diseñé e implementé...', 'Optimicé...', 'Reduciendo la latencia en un **40%** mediante **FastAPI**').\n"
                "- For each project in `projects` (if available in the context), retain the project name, repo_url, technologies, and year, and write 1 to 3 Google XYZ bullets strictly in Spanish highlighting technical architecture and impact (NEVER leave any project bullet in English).\n"
                "- In `prioritized_skills`, use Spanish category names ('Lenguajes', 'Backend', 'Cloud y DevOps', 'Bases de Datos', 'Datos e IA', 'Otros').\n"
                "- Keep standard industry technical tool names in English (e.g., Python, FastAPI, Spring Boot, AWS, Docker, Kubernetes, CI/CD, Redis, PostgreSQL), but all verbs, impact statements, roles, dates, categories, and sentences MUST be in fluent Spanish.\n"
            )
        else:
            lang_instruction = (
                "LANGUAGE DIRECTIVE:\n"
                "Write all text in executive English (~60-80 words summary, Google XYZ formula in English for bullets in both experiences and projects).\n"
            )

        system_prompt = (
            "You are an elite Executive Tech Resume Writer and ATS Optimization Specialist. "
            "Tailor the candidate's headline, profile summary, skills, work initiatives, and technical projects for the target job. "
            "You must return strictly a valid JSON object matching this schema:\n"
            f"{schema_json}\n\n"
            f"{lang_instruction}\n"
            "RULES:\n"
            "1. Output ONLY the raw JSON object. Do not include markdown code markers or preamble.\n"
            "2. Tailor `headline` to match the job title and core expertise.\n"
            "3. WORK EXPERIENCE IS THE TOP PRIORITY: You MUST include ALL companies and ALL work initiatives provided under 'Available Work Initiatives' (e.g., if a company has 2 or 3 initiatives such as AICodeFixer, Zammad on Kubernetes, and RAG, include ALL of them under that company). For each initiative, write 2 to 3 concise, high-impact bullets following the Google XYZ formula, bolding key technologies and quantifiable metrics (**FastAPI**, **50%**).\n"
            "4. For each project in `projects`, select ONLY from the projects listed under 'Available Technical Projects (GitHub)'. NEVER invent or fabricate projects. In `technologies`, include ONLY 3 to 6 core technologies relevant to the target job (NEVER list low-level utility libraries or long dependency inventories). Formulate 1 to 2 concise impactful bullets following the Google XYZ formula.\n"
            "5. Keep total resume length within the 1-page target (380-550 words) by prioritizing work experience initiatives over verbose project descriptions.\n"
            "6. In `prioritized_skills`, order the candidate's verified skills so that the job's must-have skills appear first. DO NOT add tools or technologies not in the candidate's profile.\n"
            "7. 100% FACTUAL GROUNDING (ZERO TOLERANCE): Do not hallucinate technologies, jobs, companies, or projects not present in the master profile. Fabricated entities will be automatically purged by the system."
        )

        content: TailoredResumeContent
        if self.provider == "openrouter":
            content = await self._write_openrouter(system_prompt, user_prompt)
        elif self.provider == "gemini":
            content = await self._write_gemini(system_prompt, user_prompt)
        else:
            raise ValueError("No hay proveedor de LLM configurado. Define OPENROUTER_API_KEY o GEMINI_API_KEY.")

        # Aplicar Guardrail Factual Determinista antes de renderizar
        from juanchito_assitant.agents.guardrails import FactualGuardrail
        content, alerts = FactualGuardrail.apply(content, ctx, language=language)
        self.last_guardrail_alerts = alerts

        # Ensamblar con ResumeRenderer determinista
        rendered_md = ResumeRenderer.render(
            headline=content.headline,
            profile_summary=content.profile_summary,
            experiences=[exp.model_dump() for exp in content.experiences],
            skills=content.prioritized_skills,
            matched_ctx=ctx,
            language=language,
            projects=[p.model_dump() for p in content.projects] if content.projects else None,
        )
        return rendered_md

    async def _write_openrouter(self, system_prompt: str, user_prompt: str) -> TailoredResumeContent:
        response = await call_openrouter(
            api_key=self.api_key,
            models=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_schema=TailoredResumeContent,
            timeout=self.timeout,
            http_transport=self.http_transport,
        )
        return TailoredResumeContent.model_validate(response.parse_json())

    async def _write_gemini(self, system_prompt: str, user_prompt: str) -> TailoredResumeContent:
        if not self.gemini_client:
            raise ValueError("GEMINI_API_KEY no configurada o cliente no disponible.")

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=TailoredResumeContent,
            temperature=0.2,
        )
        resp = await self.gemini_client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )
        return TailoredResumeContent.model_validate_json(resp.text)
