from datetime import datetime
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from juanchito_assitant.db.database import get_session
from juanchito_assitant.models.profile import GeneratedResume

if TYPE_CHECKING:
    from juanchito_assitant.tailor_engine import TailoringReport

_ROLE_KEYWORDS = {
    "software", "backend", "frontend", "fullstack", "full", "ai", "data", "senior",
    "sr", "junior", "jr", "lead", "engineer", "developer", "architect", "scientist",
    "devops", "cloud", "machine", "intern", "associate", "tech", "systems", "qa",
}


def parse_resume_file_to_model(file_path: Path) -> GeneratedResume | None:
    """Extrae metadatos, contenido Markdown y reporte JSON acompañante desde un archivo en disco."""
    filename = file_path.name
    if not filename.endswith(".md") or not file_path.is_file() or file_path.stat().st_size < 100:
        return None

    match = re.search(r"^resume_(.+)_(\d{8}_\d{6})\.md$", filename)
    if match:
        body = match.group(1)
        raw_ts = match.group(2)
        try:
            dt = datetime.strptime(raw_ts, "%Y%m%d_%H%M%S")
            created_at = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            created_at = raw_ts
    else:
        body = filename.removeprefix("resume_").removesuffix(".md")
        raw_ts = ""
        dt = datetime.fromtimestamp(file_path.stat().st_mtime)
        created_at = dt.strftime("%Y-%m-%d %H:%M")

    tokens = [t for t in re.split(r"[_]+", body) if t]
    split_idx = 1
    for idx, tok in enumerate(tokens):
        if idx > 0 and tok.lower() in _ROLE_KEYWORDS:
            split_idx = idx
            break

    company = " ".join(tokens[:split_idx]).replace("-", "").strip() or "Company"
    role = " ".join(tokens[split_idx:]).replace("-", " ").strip()
    role = re.sub(r"\s+", " ", role) or "Software Engineer"

    content = file_path.read_text(encoding="utf-8")
    headline_match = re.search(r'<div class="headline">\s*(.*?)\s*</div>', content, re.DOTALL)
    headline = headline_match.group(1).strip() if headline_match else None
    language = "es" if "## Perfil" in content or "## Experiencia" in content or "## Habilidades" in content else "en"
    word_count = len(content.split())
    size_bytes = len(content.encode("utf-8"))

    ats_score: int | None = None
    ats_decision: str | None = None
    job_payload: dict = {}
    evaluation_payload: dict | None = None

    json_path = file_path.with_suffix(".json")
    if json_path.is_file():
        try:
            report_data = json.loads(json_path.read_text(encoding="utf-8"))
            job_data = report_data.get("job")
            if isinstance(job_data, dict):
                job_payload = job_data
                json_comp = (job_data.get("company_name") or "").strip()
                if json_comp and json_comp.lower() not in ("null", "none", "company"):
                    company = json_comp
                json_role = (job_data.get("job_title") or "").strip()
                if json_role:
                    role = json_role
            final_eval = report_data.get("final_evaluation")
            if isinstance(final_eval, dict):
                evaluation_payload = final_eval
                ats_score = final_eval.get("total_score")
                ats_decision = final_eval.get("decision")
        except Exception:
            pass

    return GeneratedResume(
        filename=filename,
        company=company,
        role=role,
        language=language,
        headline=headline,
        markdown_content=content,
        word_count=word_count,
        size_bytes=size_bytes,
        ats_score=ats_score,
        ats_decision=ats_decision,
        job_payload=job_payload,
        evaluation_payload=evaluation_payload,
        created_at=created_at,
        timestamp_raw=raw_ts,
    )


def upsert_generated_resume(session: Session, resume: GeneratedResume) -> GeneratedResume:
    """Inserta o actualiza un currículum generado en la tabla GeneratedResume."""
    existing = session.exec(
        select(GeneratedResume).where(GeneratedResume.filename == resume.filename)
    ).first()

    if existing:
        existing.company = resume.company
        existing.role = resume.role
        existing.language = resume.language
        existing.headline = resume.headline
        existing.markdown_content = resume.markdown_content
        existing.word_count = resume.word_count
        existing.size_bytes = resume.size_bytes
        if resume.ats_score is not None:
            existing.ats_score = resume.ats_score
        if resume.ats_decision is not None:
            existing.ats_decision = resume.ats_decision
        if resume.job_payload:
            existing.job_payload = resume.job_payload
        if resume.evaluation_payload is not None:
            existing.evaluation_payload = resume.evaluation_payload
        existing.created_at = resume.created_at
        existing.timestamp_raw = resume.timestamp_raw
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume


def sync_outputs_dir_to_db(session: Session, outputs_dir: Path) -> int:
    """Sincroniza archivos .md/.json de un directorio hacia la tabla GeneratedResume."""
    if not outputs_dir.exists():
        return 0

    synced = 0
    for file_path in outputs_dir.glob("*.md"):
        parsed = parse_resume_file_to_model(file_path)
        if not parsed:
            continue

        existing = session.exec(
            select(GeneratedResume).where(GeneratedResume.filename == parsed.filename)
        ).first()
        if existing is None:
            session.add(parsed)
            synced += 1
        else:
            # Si en disco se agregó una evaluación JSON que en DB aún no estaba, actualizarla
            updated = False
            if existing.evaluation_payload is None and parsed.evaluation_payload is not None:
                existing.evaluation_payload = parsed.evaluation_payload
                existing.ats_score = parsed.ats_score
                existing.ats_decision = parsed.ats_decision
                updated = True
            if existing.markdown_content != parsed.markdown_content:
                existing.markdown_content = parsed.markdown_content
                existing.word_count = parsed.word_count
                existing.size_bytes = parsed.size_bytes
                updated = True
            if updated:
                session.add(existing)
                synced += 1

    if synced > 0:
        session.commit()
    return synced


def persist_tailoring_report(
    report: "TailoringReport",
    filename: str,
    timestamp_raw: str,
    session: Session | None = None,
) -> None:
    """Guarda el resultado de TailoringEngine directamente en la tabla GeneratedResume."""
    content = report.final_markdown
    headline_match = re.search(r'<div class="headline">\s*(.*?)\s*</div>', content, re.DOTALL)
    headline = headline_match.group(1).strip() if headline_match else None

    try:
        dt = datetime.strptime(timestamp_raw, "%Y%m%d_%H%M%S")
        created_at = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    company = (report.job.company_name or "").strip()
    if not company or company.lower() in ("null", "none"):
        company = "Company"
    role = (report.job.job_title or "Software Engineer").strip()

    eval_dump = report.final_evaluation.model_dump(mode="json") if report.final_evaluation else None
    ats_score = report.final_evaluation.total_score if report.final_evaluation else None
    ats_decision = report.final_evaluation.decision if report.final_evaluation else None

    record = GeneratedResume(
        filename=filename,
        company=company,
        role=role,
        language=report.language,
        headline=headline,
        markdown_content=content,
        word_count=len(content.split()),
        size_bytes=len(content.encode("utf-8")),
        ats_score=ats_score,
        ats_decision=ats_decision,
        job_payload=report.job.model_dump(mode="json"),
        evaluation_payload=eval_dump,
        created_at=created_at,
        timestamp_raw=timestamp_raw,
    )

    if session is not None:
        upsert_generated_resume(session, record)
    else:
        with get_session() as db_sess:
            upsert_generated_resume(db_sess, record)
