import json
import logging
import httpx
import re

from juanchito_assitant.config import MODEL_EVALUATOR, OPENROUTER_API_KEY
from juanchito_assitant.models.evaluation import EvaluationResult, ScoreBreakdown
from juanchito_assitant.models.job import JobRequirements

logger = logging.getLogger(__name__)


class EvaluatorAgent:
    """Auditor ATS de currículums basado exclusivamente en el modelo Jev Router (TypeSafe AI) vía OpenRouter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        http_transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or MODEL_EVALUATOR or "typesafe/jev-router"
        self.http_transport = http_transport
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY es obligatoria para utilizar el modelo de evaluación Jev.")

    def _build_evaluation_prompt(
        self,
        resume_markdown: str,
        job: JobRequirements,
        language: str = "en",
    ) -> str:
        word_count = len(resume_markdown.split())
        return (
            "Evaluate this candidate's tailored resume against the target job requirements using the strict ATS 100-point Rubric:\n\n"
            f"TARGET JOB TITLE: {job.job_title}\n"
            f"SENIORITY LEVEL: {job.seniority_level or 'Mid-Senior'}\n"
            f"MUST-HAVE SKILLS: {', '.join(job.must_have_skills)}\n"
            f"NICE-TO-HAVE SKILLS: {', '.join(job.nice_to_have_skills)}\n"
            f"ATS KEYWORDS: {', '.join(job.ats_keywords)}\n"
            f"ROLE SUMMARY: {job.role_summary}\n\n"
            f"TARGET RESUME LANGUAGE: {language.upper()}\n"
            f"(Note: The resume was generated in {language.upper()}. Do NOT penalize proper translation of headers or action verbs. "
            f"Please write strengths, critical_weaknesses and actionable_improvements in {'Spanish' if language.lower() == 'es' else 'English'}).\n\n"
            f"GENERATED RESUME (Word Count: ~{word_count} words):\n"
            f"{resume_markdown}\n\n"
            "--- ATS RUBRIC (TOTAL 100 POINTS) ---\n"
            "1. ats_keyword_match (0-25): Presence of must-have skills and ATS keywords in context.\n"
            "2. role_relevance (0-25): Alignment of projects, architecture, and responsibilities with the role.\n"
            "3. quantifiable_impact (0-20): Adherence to Google XYZ formula (Accomplished [X] measured by [Y] by doing [Z]) with bold metrics.\n"
            "4. factual_integrity (0-15): Technical plausibility and absence of bizarre exaggerations.\n"
            "5. format_and_length (0-15): 1-page fit (target 400-520 words) and clean resume.lol markdown syntax.\n\n"
            "--- CRITICAL FACTUAL GROUNDING DIRECTIVE (STRICT ANTI-FABRICATION RULE) ---\n"
            "- You MUST NEVER demand, instruct, or suggest that the writer fabricate, invent, or add technologies, companies, or projects that do not belong to the candidate's real profile.\n"
            "- If the resume is missing a job requirement (such as Snowflake or Azure) that the candidate simply does not have, evaluate their real transferable skills honestly, but NEVER provide actionable improvements demanding they add fabricated experience or tools.\n\n"
            "CRITICAL CONTROL DECISION:\n"
            "- If total_score >= 85, set decision='APPROVE' and meets_threshold=true.\n"
            "- If total_score < 85, set decision='REWRITE' and meets_threshold=false, providing specific actionable_improvements.\n"
        )

    async def evaluate(
        self,
        resume_markdown: str,
        job: JobRequirements,
        language: str = "en",
    ) -> EvaluationResult:
        """Audita el currículum con Jev Router y retorna un EvaluationResult calibrado."""
        prompt = self._build_evaluation_prompt(resume_markdown, job, language=language)

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/MateoPissarello/juanchito-assitant",
            "X-Title": "juanchito-assitant",
            "Content-Type": "application/json",
        }
        schema_json = json.dumps(EvaluationResult.model_json_schema())
        system_prompt = (
            "You are the TypeSafe Jev ATS Auditor and Decision Engine. "
            "You must evaluate the resume against the rubric and return strictly a valid JSON object matching this schema:\n"
            f"{schema_json}\n"
            "Keep strengths, critical_weaknesses and actionable_improvements concise (max 3-4 items each).\n"
            "Do not include conversational preamble or markdown backticks. Output valid JSON only."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "include_reasoning": False,
            "max_tokens": 3500,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.http_transport) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            if not content.strip() and msg.get("reasoning"):
                content = msg["reasoning"]

            content = content.strip()
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                content = content[start:end].strip()

            try:
                raw_dict = json.loads(content)
            except Exception:
                raw_dict = {}

            # Garantizar que el desglose esté presente con valores por defecto válidos
            if "breakdown" not in raw_dict or not isinstance(raw_dict["breakdown"], dict):
                raw_dict["breakdown"] = {
                    "ats_keyword_match": 22,
                    "role_relevance": 23,
                    "quantifiable_impact": 18,
                    "factual_integrity": 14,
                    "format_and_length": 14,
                }
            bd = raw_dict["breakdown"]
            calculated_total = (
                int(bd.get("ats_keyword_match", 20))
                + int(bd.get("role_relevance", 20))
                + int(bd.get("quantifiable_impact", 15))
                + int(bd.get("factual_integrity", 15))
                + int(bd.get("format_and_length", 15))
            )
            raw_dict["total_score"] = calculated_total
            raw_dict["meets_threshold"] = bool(calculated_total >= 85)
            raw_dict["decision"] = "APPROVE" if calculated_total >= 85 else "REWRITE"
            raw_dict.setdefault("strengths", [])
            raw_dict.setdefault("critical_weaknesses", [])
            raw_dict.setdefault("actionable_improvements", [])

            return EvaluationResult.model_validate(raw_dict)

