from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import pytest
from typer.testing import CliRunner
from sqlmodel import SQLModel, create_engine, Session

from juanchito_assitant.cli import app
from juanchito_assitant.models.job import JobRequirements
from juanchito_assitant.models.evaluation import EvaluationResult, ScoreBreakdown
from juanchito_assitant.models.profile import PersonalInfo, TrackedRepo
from juanchito_assitant.tailor_engine import TailoringReport

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Juanchito Assistant" in result.stdout
    assert "status" in result.stdout
    assert "tailor" in result.stdout
    assert "audit" in result.stdout
    assert "repo" in result.stdout
    assert "sync" in result.stdout
    assert "web" in result.stdout


def test_cli_web_help():
    result = runner.invoke(app, ["web", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.stdout
    assert "--host" in result.stdout



def test_cli_status():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Diagnóstico del Sistema" in result.stdout
    assert "Base de Datos (SQLite)" in result.stdout


def test_cli_audit():
    result = runner.invoke(app, ["audit"])
    assert result.exit_code == 0
    assert "Información Personal" in result.stdout
    assert "Experiencia Laboral" in result.stdout


def test_cli_repo_crud():
    # 1. Agregar repo
    res_add = runner.invoke(app, ["repo", "add", "mock-cli-repo", "--branch", "dev", "--category", "Testing"])
    assert res_add.exit_code == 0
    assert "agregado con éxito" in res_add.stdout

    # 2. Listar
    res_list = runner.invoke(app, ["repo", "list"])
    assert res_list.exit_code == 0
    assert "mock-cli-repo" in res_list.stdout

    # 3. Toggle
    res_toggle = runner.invoke(app, ["repo", "toggle", "mock-cli-repo"])
    assert res_toggle.exit_code == 0
    assert "INACTIVO" in res_toggle.stdout

    # 4. Remover
    res_remove = runner.invoke(app, ["repo", "remove", "mock-cli-repo"])
    assert res_remove.exit_code == 0
    assert "eliminado de SQLite con éxito" in res_remove.stdout


def test_cli_tailor_help():
    result = runner.invoke(app, ["tailor", "--help"])
    assert result.exit_code == 0
    assert "--url" in result.stdout
    assert "--file" in result.stdout
    assert "--max-iterations" in result.stdout


@patch("juanchito_assitant.cli.JobAnalyzerAgent")
@patch("juanchito_assitant.cli.TailoringEngine")
def test_cli_tailor_flow(mock_engine_cls, mock_analyzer_cls, tmp_path):
    mock_analyzer = MagicMock()
    mock_analyzer.analyze_job = AsyncMock(
        return_value=JobRequirements(
            job_title="Senior Backend Engineer",
            company_name="Nubank",
            seniority_level="Senior",
            must_have_skills=["Python", "AWS"],
            nice_to_have_skills=["Kubernetes"],
            core_responsibilities=["Build microservices"],
            ats_keywords=["Scalability", "Microservices"],
            role_summary="Lead backend initiatives in banking.",
        )
    )
    mock_analyzer_cls.return_value = mock_analyzer

    dummy_output_file = tmp_path / "resume_output.md"
    dummy_output_file.write_text("# Resume", encoding="utf-8")

    mock_engine = MagicMock()
    mock_engine.run = AsyncMock(
        return_value=TailoringReport(
            job=mock_analyzer.analyze_job.return_value,
            final_markdown="# Tailored Resume Content\nWith 100 words...",
            final_evaluation=EvaluationResult(
                total_score=92,
                meets_threshold=True,
                decision="APPROVE",
                breakdown=ScoreBreakdown(
                    ats_keyword_match=25,
                    role_relevance=24,
                    quantifiable_impact=18,
                    factual_integrity=13,
                    format_and_length=12,
                ),
                strengths=["Excellent match."],
                critical_weaknesses=[],
                actionable_improvements=[],
            ),
            iterations=[],
            output_file_path=dummy_output_file,
        )
    )
    mock_engine_cls.return_value = mock_engine

    # Ejecutar pasando texto de vacante y respondiendo 'y' a la confirmación
    result = runner.invoke(app, ["tailor", "Looking for Senior Backend Engineer in Nubank", "--dry-run"], input="y\n")
    assert result.exit_code == 0
    assert "Nubank" in result.stdout
    assert "Scorecard de Auditoría ATS" in result.stdout
    assert "92 / 100" in result.stdout
    assert "APPROVE" in result.stdout
