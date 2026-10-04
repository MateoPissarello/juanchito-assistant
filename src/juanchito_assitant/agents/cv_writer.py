import json
import logging
import re
import httpx
from pydantic import BaseModel, Field

from juanchito_assitant.agents.matcher import MatchedContext
from juanchito_assitant.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MODEL_CV_WRITER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
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


class TailoredResumeContent(BaseModel):
    headline: str = Field(description="Titular profesional adaptado a la vacante.")
    profile_summary: str = Field(description="1 párrafo conciso en inglés enfocado en el match con el rol.")
    experiences: list[TailoredExperience] = Field(default_factory=list)
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
        model: str | None = None,
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
            self.model = model or MODEL_CV_WRITER or OPENROUTER_MODEL
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

    def _build_context_prompt(self, ctx: MatchedContext, feedback: list[str] | None = None) -> str:
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
                for b in p.bullets:
                    work_str += f"  - {b}\n"

        skills_dict: dict[str, list[str]] = {cat.category: cat.skills for cat in ctx.skills[:5]}

        feedback_section = ""
        if feedback:
            feedback_section = (
                "\n\n--- CRITICAL EVALUATOR FEEDBACK (MUST FIX IN THIS REVISION) ---\n"
                + "\n".join(f"- {f}" for f in feedback)
                + "\n---------------------------------------------------------------\n"
            )

        job = ctx.target_job
        return (
            f"TARGET JOB TITLE: {job.job_title}\n"
            f"TARGET COMPANY: {job.company_name or 'Hiring Company'}\n"
            f"SENIORITY LEVEL: {job.seniority_level or 'Mid-Senior'}\n"
            f"MUST-HAVE SKILLS: {', '.join(job.must_have_skills)}\n"
            f"NICE-TO-HAVE SKILLS: {', '.join(job.nice_to_have_skills)}\n"
            f"ATS KEYWORDS: {', '.join(job.ats_keywords)}\n"
            f"ROLE SUMMARY: {job.role_summary}\n\n"
            f"{feedback_section}\n"
            f"--- CANDIDATE MASTER PROFILE (FACTUAL TRUTH - DO NOT INVENT) ---\n"
            f"Personal: {ctx.personal_info.full_name} | {ctx.personal_info.location}\n"
            f"Available Skills:\n{json.dumps(skills_dict, indent=2)}\n"
            f"Available Work Initiatives:\n{work_str}\n"
        )

    async def write_resume(self, ctx: MatchedContext, feedback: list[str] | None = None) -> str:
        """Genera el contenido estructurado adaptado con LLM y lo renderiza con ResumeRenderer."""
        user_prompt = self._build_context_prompt(ctx, feedback)
        schema_json = json.dumps(TailoredResumeContent.model_json_schema())

        system_prompt = (
            "You are an elite Executive Tech Resume Writer and ATS Optimization Specialist. "
            "Tailor the candidate's headline, profile summary, skills, and work initiatives for the target job. "
            "You must return strictly a valid JSON object matching this schema:\n"
            f"{schema_json}\n\n"
            "RULES:\n"
            "1. Output ONLY the raw JSON object. Do not include markdown code markers or preamble.\n"
            "2. Tailor `headline` to match the job title and core expertise.\n"
            "3. Tailor `profile_summary` to 1 powerful paragraph in English (~60-80 words) emphasizing cloud, distributed systems, and backend mastery.\n"
            "4. For each experience, reformulate 2 to 4 bullets following the Google XYZ formula: Accomplished [X] measured by [Y] by doing [Z], bolding key technologies and quantifiable metrics (**FastAPI**, **50%**).\n"
            "5. In `prioritized_skills`, order categories and skills so that the job's must-have skills appear first.\n"
            "6. 100% FACTUAL: Do not hallucinate technologies or jobs not present in the master profile."
        )

        content: TailoredResumeContent
        if self.provider == "openrouter":
            content = await self._write_openrouter(system_prompt, user_prompt)
        elif self.provider == "gemini":
            content = await self._write_gemini(system_prompt, user_prompt)
        else:
            raise ValueError("No hay proveedor de LLM configurado. Define OPENROUTER_API_KEY o GEMINI_API_KEY.")

        # Ensamblar con ResumeRenderer determinista
        rendered_md = ResumeRenderer.render(
            headline=content.headline,
            profile_summary=content.profile_summary,
            experiences=[exp.model_dump() for exp in content.experiences],
            skills=content.prioritized_skills,
            matched_ctx=ctx,
        )
        return rendered_md

    async def _write_openrouter(self, system_prompt: str, user_prompt: str) -> TailoredResumeContent:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/MateoPissarello/juanchito-assitant",
            "X-Title": "juanchito-assitant",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.http_transport) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return TailoredResumeContent.model_validate_json(raw_text)

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
