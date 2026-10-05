from datetime import datetime
from pathlib import Path
import re
from typing import Any, Awaitable, Callable
from pydantic import BaseModel, Field
from sqlmodel import Session

from juanchito_assitant.agents.cv_writer import WriterAgent
from juanchito_assitant.agents.evaluator import EvaluatorAgent
from juanchito_assitant.agents.job_analyzer import JobAnalyzerAgent
from juanchito_assitant.agents.matcher import MatcherAgent
from juanchito_assitant.config import OUTPUTS_DIR
from juanchito_assitant.models.evaluation import EvaluationResult, IterationRecord
from juanchito_assitant.models.job import JobRequirements

ProgressCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name).strip("_")


class TailoringReport(BaseModel):
    """Reporte completo de la ejecución del motor multi-agente."""

    job: JobRequirements
    final_markdown: str
    final_evaluation: EvaluationResult
    iterations: list[IterationRecord] = Field(default_factory=list)
    output_file_path: Path
    language: str = "en"


class TailoringEngine:
    """Orquestador del pipeline multi-agente de adaptación de currículums."""

    def __init__(
        self,
        session: Session,
        job_analyzer: JobAnalyzerAgent | None = None,
        matcher: MatcherAgent | None = None,
        writer: WriterAgent | None = None,
        evaluator: EvaluatorAgent | None = None,
    ):
        self.session = session
        self.job_analyzer = job_analyzer or JobAnalyzerAgent()
        self.matcher = matcher or MatcherAgent(session)
        self.writer = writer or WriterAgent()
        self.evaluator = evaluator or EvaluatorAgent()

    async def run(
        self,
        job_input: str,
        max_iterations: int = 2,
        language: str = "en",
        on_progress: ProgressCallback | None = None,
    ) -> TailoringReport:
        """Ejecuta el flujo completo: análisis de vacante, matching, redacción y auditoría ATS."""
        # 1. Analizar vacante
        if on_progress:
            await on_progress(
                "analyzing",
                {
                    "message": "Analizando requisitos y palabras clave de la vacante...",
                    "step": 1,
                    "total_steps": 4,
                    "language": language,
                },
            )
        job = await self.job_analyzer.analyze_job(job_input)

        # 2. Selección de activos desde SQLite
        if on_progress:
            await on_progress(
                "matching",
                {
                    "message": f"Seleccionando experiencias y proyectos relevantes para {job.job_title}...",
                    "step": 2,
                    "total_steps": 4,
                    "job_title": job.job_title,
                    "company": job.company_name or "Empresa",
                    "keywords": job.ats_keywords[:8],
                    "language": language,
                },
            )
        matched_ctx = self.matcher.match(job)

        iterations: list[IterationRecord] = []
        feedback: list[str] | None = None
        current_markdown = ""
        current_evaluation: EvaluationResult | None = None

        # 3. Bucle reflexivo de redacción y auditoría ATS
        for i in range(1, max_iterations + 1):
            if on_progress:
                iter_label = f" (Ronda {i}/{max_iterations})" if max_iterations > 1 else ""
                await on_progress(
                    "writing",
                    {
                        "message": f"Redactando y cuantificando logros con métricas{iter_label}...",
                        "step": 3,
                        "total_steps": 4,
                        "iteration": i,
                        "language": language,
                    },
                )
            current_markdown = await self.writer.write_resume(
                matched_ctx,
                feedback=feedback,
                language=language,
            )

            if on_progress:
                await on_progress(
                    "evaluating",
                    {
                        "message": f"Auditando compatibilidad ATS y calidad del currículum{iter_label}...",
                        "step": 4,
                        "total_steps": 4,
                        "iteration": i,
                        "language": language,
                    },
                )
            current_evaluation = await self.evaluator.evaluate(
                current_markdown,
                job,
                language=language,
            )

            record = IterationRecord(
                iteration=i,
                generated_markdown=current_markdown,
                evaluation=current_evaluation,
            )
            iterations.append(record)

            if current_evaluation.decision == "APPROVE" or current_evaluation.meets_threshold:
                break

            # Si no aprueba y quedan iteraciones, preparar feedback para el Writer
            feedback = (
                current_evaluation.actionable_improvements
                + [f"Deficiencia crítica: {w}" for w in current_evaluation.critical_weaknesses]
            )

        assert current_evaluation is not None

        # 4. Guardar archivo adaptado en data/outputs/
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        company_tag = _sanitize_filename(job.company_name or "company")
        title_tag = _sanitize_filename(job.job_title)
        filename = f"resume_{company_tag}_{title_tag}_{timestamp}.md"
        output_path = OUTPUTS_DIR / filename
        output_path.write_text(current_markdown, encoding="utf-8")

        report = TailoringReport(
            job=job,
            final_markdown=current_markdown,
            final_evaluation=current_evaluation,
            iterations=iterations,
            output_file_path=output_path,
            language=language,
        )

        if on_progress:
            await on_progress(
                "completed",
                {
                    "message": "¡Currículum adaptado y optimizado con éxito!",
                    "step": 4,
                    "total_steps": 4,
                    "report": report.model_dump(mode="json"),
                },
            )

        return report

