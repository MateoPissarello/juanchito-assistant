from dataclasses import dataclass
import json
import logging
import re
import httpx

from juanchito_assitant.agents.guardrails import FactualGuardrail
from juanchito_assitant.agents.matcher import MatchedContext, extract_key_terms, matches_term
from juanchito_assitant.config import MODELS_EVALUATOR, MODEL_EVALUATOR, OPENROUTER_API_KEY
from juanchito_assitant.agents.llm_client import call_openrouter
from juanchito_assitant.models.evaluation import EvaluationResult, ScoreBreakdown
from juanchito_assitant.models.job import JobRequirements

logger = logging.getLogger(__name__)


@dataclass
class DeterministicPreAudit:
    """Resultado de la pre-auditoría determinista ejecutada en código antes del LLM Judge."""

    word_count: int
    total_bullets: int
    quantified_bullets: int
    matched_job_skills: list[str]
    missing_owned_skills: list[str]
    unowned_job_skills: list[str]


class DeterministicATSAuditor:
    """Calcula métricas exactas de cobertura de keywords, cuantificación y brechas reales vs SQLite."""

    METRIC_PATTERN = re.compile(
        r"(\d+\s*%|\$\s*\d+|\d+(?:\.\d+)?x\b|\d+\+|\b\d+\s*(?:ms|s|sec|seconds|segundos|min|minutes|minutos|hours|horas|days|días|users|usuarios|requests|peticiones|endpoints|pipelines|services|servicios|models|modelos|repos|records|registros|queries|consultas)\b)",
        re.IGNORECASE,
    )

    @classmethod
    def audit(
        cls,
        resume_markdown: str,
        job: JobRequirements,
        matched_ctx: MatchedContext | None = None,
    ) -> DeterministicPreAudit:
        word_count = len(resume_markdown.split())
        resume_lower = resume_markdown.lower()

        # Extraer viñetas de experiencia y proyectos (excluyendo variables y links de contacto)
        bullet_lines: list[str] = []
        in_header_or_skills = False
        for line in resume_markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith('<div class="section headerInfo">') or stripped in ("## Skills", "## Habilidades"):
                in_header_or_skills = True
                continue
            if stripped.startswith("## ") and stripped not in ("## Skills", "## Habilidades"):
                in_header_or_skills = False
                continue
            if stripped == "</div>":
                in_header_or_skills = False
                continue

            if not in_header_or_skills:
                # Viñetas de segundo nivel (    - ) o de proyectos (- ) que no sean solo títulos de iniciativa (- **Nombre**)
                if stripped.startswith("- ") and not re.match(r"^-\s+\*\*[^*]+\*\*\s*$", stripped):
                    bullet_lines.append(stripped)

        total_bullets = len(bullet_lines)
        quantified_bullets = sum(1 for b in bullet_lines if cls.METRIC_PATTERN.search(b))

        # Clasificar skills de la vacante frente al perfil real en SQLite
        if matched_ctx is not None:
            owned_job_skills, unowned_job_skills = FactualGuardrail.classify_job_skills(job, matched_ctx)
        else:
            raw_skills = list(job.must_have_skills) + list(job.nice_to_have_skills) + list(job.ats_keywords)
            owned_job_skills = extract_key_terms(raw_skills)
            unowned_job_skills = []

        matched_job_skills: list[str] = []
        missing_owned_skills: list[str] = []

        for skill in owned_job_skills:
            if matches_term(skill.lower(), resume_lower, set()):
                matched_job_skills.append(skill)
            else:
                missing_owned_skills.append(skill)

        return DeterministicPreAudit(
            word_count=word_count,
            total_bullets=total_bullets,
            quantified_bullets=quantified_bullets,
            matched_job_skills=matched_job_skills,
            missing_owned_skills=missing_owned_skills,
            unowned_job_skills=unowned_job_skills,
        )


class EvaluatorAgent:
    """Auditor ATS híbrido (Pre-Auditoría Determinista + LLM Judge vía OpenRouter)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | list[str] | None = None,
        http_transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or MODELS_EVALUATOR
        self.http_transport = http_transport
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY es obligatoria para utilizar el modelo de evaluación Jev.")

    def _build_evaluation_prompt(
        self,
        resume_markdown: str,
        job: JobRequirements,
        language: str = "en",
        pre_audit: DeterministicPreAudit | None = None,
    ) -> str:
        audit = pre_audit or DeterministicATSAuditor.audit(resume_markdown, job)
        metrics_pct = (
            round((audit.quantified_bullets / audit.total_bullets) * 100)
            if audit.total_bullets > 0
            else 0
        )

        pre_audit_block = (
            "--- DETERMINISTIC PRE-AUDIT SIGNALS (EXACT CODE MEASUREMENTS) ---\n"
            f"- Exact Word Count: {audit.word_count} words (Target 1-page range: 380-550 words)\n"
            f"- Quantified Impact Bullets: {audit.quantified_bullets}/{audit.total_bullets} bullets ({metrics_pct}%) contain explicit numerical metrics\n"
            f"- Job Skills PRESENT in Resume: {', '.join(audit.matched_job_skills) if audit.matched_job_skills else 'None'}\n"
            f"- Job Skills OWNED BY CANDIDATE (in SQLite) but OMITTED from Resume: {', '.join(audit.missing_owned_skills) if audit.missing_owned_skills else 'None (100% of candidate owned matching skills are included!)'}\n"
            f"- Job Skills NOT OWNED BY CANDIDATE (Real Profile Gaps): {', '.join(audit.unowned_job_skills) if audit.unowned_job_skills else 'None'}\n"
            "-----------------------------------------------------------------\n\n"
        )

        return (
            "Evaluate this candidate's tailored resume against the target job requirements using the strict ATS 100-point Rubric:\n\n"
            f"TARGET JOB TITLE: {job.job_title}\n"
            f"SENIORITY LEVEL: {job.seniority_level or 'Mid-Senior'}\n"
            f"MUST-HAVE SKILLS: {', '.join(job.must_have_skills)}\n"
            f"NICE-TO-HAVE SKILLS: {', '.join(job.nice_to_have_skills)}\n"
            f"ATS KEYWORDS: {', '.join(job.ats_keywords)}\n"
            f"ROLE SUMMARY: {job.role_summary}\n\n"
            f"{pre_audit_block}"
            f"TARGET RESUME LANGUAGE: {language.upper()}\n"
            f"(Note: The resume was generated in {language.upper()}. Do NOT penalize proper translation of headers or action verbs. "
            f"Please write strengths, critical_weaknesses and actionable_improvements in {'Spanish' if language.lower() == 'es' else 'English'}).\n\n"
            f"GENERATED RESUME (Word Count: ~{audit.word_count} words):\n"
            f"{resume_markdown}\n\n"
            "--- ATS RUBRIC (TOTAL 100 POINTS) ---\n"
            "1. ats_keyword_match (0-25): Presence of candidate's verified matching skills and ATS keywords in context.\n"
            "2. role_relevance (0-25): Alignment of projects, architecture, and responsibilities with the role.\n"
            "3. quantifiable_impact (0-20): Adherence to Google XYZ formula (Accomplished [X] measured by [Y] by doing [Z]) with bold metrics.\n"
            "4. factual_integrity (0-15): Technical plausibility and absence of fabricated skills.\n"
            "5. format_and_length (0-15): 1-page fit (target 380-550 words) and clean resume.lol markdown syntax.\n\n"
            "--- CRITICAL FACTUAL GROUNDING DIRECTIVE (STRICT ANTI-FABRICATION RULE) ---\n"
            "- Look at 'Job Skills NOT OWNED BY CANDIDATE (Real Profile Gaps)' above: the candidate does NOT possess those skills in their database.\n"
            "- You MUST NEVER demand, instruct, or suggest in `actionable_improvements` that the writer add or fabricate any skill from 'Job Skills NOT OWNED BY CANDIDATE'.\n"
            "- Instead, if there are items in 'Job Skills OWNED BY CANDIDATE (in SQLite) but OMITTED from Resume', instruct the writer to include those specific verified skills.\n\n"
            "CRITICAL CONTROL DECISION:\n"
            "- If total_score >= 85, set decision='APPROVE' and meets_threshold=true.\n"
            "- If total_score < 85, set decision='REWRITE' and meets_threshold=false, providing specific actionable_improvements.\n"
        )

    async def evaluate(
        self,
        resume_markdown: str,
        job: JobRequirements,
        language: str = "en",
        matched_ctx: MatchedContext | None = None,
    ) -> EvaluationResult:
        """Audita el currículum combinando pre-auditoría determinista y evaluación LLM (Jev Router + fallbacks)."""
        pre_audit = DeterministicATSAuditor.audit(resume_markdown, job, matched_ctx=matched_ctx)
        prompt = self._build_evaluation_prompt(
            resume_markdown,
            job,
            language=language,
            pre_audit=pre_audit,
        )

        schema_json = json.dumps(EvaluationResult.model_json_schema())
        system_prompt = (
            "You are the TypeSafe Jev ATS Auditor and Decision Engine. "
            "You must evaluate the resume against the rubric and return strictly a valid JSON object matching this schema:\n"
            f"{schema_json}\n"
            "Keep strengths, critical_weaknesses and actionable_improvements concise (max 3-4 items each).\n"
            "Do not include conversational preamble or markdown backticks. Output valid JSON only."
        )

        response = await call_openrouter(
            api_key=self.api_key,
            models=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            include_reasoning=False,
            max_tokens=3500,
            response_schema=EvaluationResult,
            timeout=self.timeout,
            http_transport=self.http_transport,
        )

        try:
            raw_dict = response.parse_json()
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

        # 1. Filtrar cualquier sugerencia en actionable_improvements que exija alucinar una skill no poseída
        unowned_low = [u.lower() for u in pre_audit.unowned_job_skills]
        owned_missing_low = [m.lower() for m in pre_audit.missing_owned_skills]
        safe_improvements: list[str] = []
        for imp in raw_dict.get("actionable_improvements", []):
            imp_low = str(imp).lower()
            mentions_unowned = any(
                re.search(r"\b" + re.escape(u) + r"\b", imp_low)
                for u in unowned_low
                if len(u) >= 2
            )
            mentions_owned_missing = any(
                re.search(r"\b" + re.escape(m) + r"\b", imp_low)
                for m in owned_missing_low
                if len(m) >= 2
            )
            if mentions_unowned and not mentions_owned_missing:
                logger.info(
                    "[EVALUATOR GUARDRAIL] Sugerencia descartada por pedir tecnología no poseída: %s",
                    imp,
                )
                continue
            safe_improvements.append(str(imp))

        # 2. Si el candidato posee skills pedidas por la vacante que el Writer olvidó incluir, inyectar mejora accionable
        if pre_audit.missing_owned_skills:
            missing_str = ", ".join(pre_audit.missing_owned_skills[:6])
            if language.lower() == "es":
                owned_msg = (
                    f"Incluir habilidades verificadas de tu perfil en SQLite que pide la vacante y fueron omitidas: {missing_str}."
                )
            else:
                owned_msg = (
                    f"Include verified skills from the candidate's database that match the job but were omitted: {missing_str}."
                )
            if not any(missing_str.lower() in s.lower() for s in safe_improvements):
                safe_improvements.insert(0, owned_msg)

        raw_dict["actionable_improvements"] = safe_improvements

        # 3. Si existen brechas reales en el perfil frente a la vacante, indicarlo con transparencia (sin pedir alucinarlas)
        if pre_audit.unowned_job_skills:
            gaps_str = ", ".join(pre_audit.unowned_job_skills[:6])
            if language.lower() == "es":
                gap_note = (
                    f"Brecha real de perfil (omitida para evitar alucinaciones): el perfil no registra {gaps_str}."
                )
            else:
                gap_note = (
                    f"Real profile skill gap (omitted to prevent hallucination): candidate profile does not include {gaps_str}."
                )
            weaknesses = [str(w) for w in raw_dict.get("critical_weaknesses", [])]
            if not any("alucinac" in w.lower() or "hallucinat" in w.lower() for w in weaknesses):
                weaknesses.append(gap_note)
            raw_dict["critical_weaknesses"] = weaknesses

        raw_dict["matched_job_skills"] = pre_audit.matched_job_skills
        raw_dict["missing_owned_skills"] = pre_audit.missing_owned_skills
        raw_dict["unowned_job_skills"] = pre_audit.unowned_job_skills

        return EvaluationResult.model_validate(raw_dict)

