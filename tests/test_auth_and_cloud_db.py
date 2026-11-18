from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from typer.testing import CliRunner

from juanchito_assitant.cli import app as cli_app
from juanchito_assitant.db.cloud_sync import push_local_to_target_db
from juanchito_assitant.db.database import normalize_database_url, resolve_database_url
from juanchito_assitant.db.resume_store import persist_tailoring_report
from juanchito_assitant.models.evaluation import EvaluationResult, ScoreBreakdown
from juanchito_assitant.models.job import JobRequirements
from juanchito_assitant.models.profile import (
    Certification,
    GeneratedResume,
    PersonalInfo,
    SkillCategory,
    TrackedRepo,
    WorkExperience,
    WorkProject,
)
from juanchito_assitant.tailor_engine import TailoringReport
from juanchito_assitant.web.api import get_db
from juanchito_assitant.web.app import create_app


def test_normalize_and_resolve_database_url(tmp_path, monkeypatch):
    assert normalize_database_url("postgres://user:pass@ep-cool.neon.tech/neondb") == (
        "postgresql+psycopg://user:pass@ep-cool.neon.tech/neondb"
    )
    assert normalize_database_url("postgresql://user:pass@db.supabase.co:5432/postgres") == (
        "postgresql+psycopg://user:pass@db.supabase.co:5432/postgres"
    )
    assert normalize_database_url("sqlite:///data/profile.db") == "sqlite:///data/profile.db"

    # Cuando DATABASE_URL está en el entorno y se usa el DB_PATH por defecto, resuelve a Postgres
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    assert resolve_database_url() == "postgresql+psycopg://u:p@host/db"

    # Pero si un test pasa un db_path explícito distinto al global, respeta el SQLite aislado
    custom_db = tmp_path / "isolated.db"
    assert resolve_database_url(db_path=custom_db) == f"sqlite:///{custom_db}"


def test_auth_gate_protects_endpoints_and_allows_login_logout(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "mateo")
    monkeypatch.setenv("ADMIN_PASSWORD", "super-secret-render-2026")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-hmac-secret-key")

    test_db = tmp_path / "test_auth.db"
    test_engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)

    def override_get_db():
        with Session(test_engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        # 1. /api/health debe permanecer público para el healthcheck de Render
        health_res = client.get("/api/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"

        # 2. /api/auth/status debe indicar que auth_enabled=True y authenticated=False
        status_res = client.get("/api/auth/status")
        assert status_res.status_code == 200
        assert status_res.json() == {
            "authenticated": False,
            "auth_enabled": True,
            "username": None,
        }

        # 3. Endpoints privados deben responder 401 sin sesión
        assert client.get("/api/profile").status_code == 401
        assert client.get("/api/repos").status_code == 401
        assert client.get("/api/tailor/history").status_code == 401

        # 4. Login con contraseña incorrecta debe fallar con 401
        bad_login = client.post(
            "/api/auth/login",
            json={"username": "mateo", "password": "wrong-password"},
        )
        assert bad_login.status_code == 401

        # 5. Login con credenciales válidas debe emitir cookie HttpOnly y autenticar
        ok_login = client.post(
            "/api/auth/login",
            json={"username": "mateo", "password": "super-secret-render-2026"},
        )
        assert ok_login.status_code == 200
        assert ok_login.json()["authenticated"] is True
        assert ok_login.json()["username"] == "mateo"
        assert "juanchito_session" in ok_login.cookies

        # 6. Con la cookie activa, los endpoints privados responden 200 OK
        profile_res = client.get("/api/profile")
        assert profile_res.status_code == 200
        assert "personal" in profile_res.json()

        # 7. Logout revoca la cookie y bloquea nuevamente el acceso
        logout_res = client.post("/api/auth/logout")
        assert logout_res.status_code == 200
        assert logout_res.json()["authenticated"] is False

        assert client.get("/api/profile").status_code == 401


def test_history_persists_in_database_without_disk_files(tmp_path, monkeypatch):
    """Simula un reinicio de contenedor en Render donde data/outputs/ está vacío pero la DB conserva los CVs."""
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    empty_outputs = tmp_path / "empty_outputs"
    empty_outputs.mkdir()
    monkeypatch.setattr("juanchito_assitant.web.api.OUTPUTS_DIR", empty_outputs)

    test_db = tmp_path / "cloud_sim.db"
    test_engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)

    mock_job = JobRequirements(
        job_title="Senior Backend Engineer",
        company_name="RenderCloud",
        role_summary="Distributed Python Services",
        must_have_skills=["Python", "FastAPI", "PostgreSQL"],
    )
    mock_eval = EvaluationResult(
        total_score=94,
        decision="APPROVE",
        meets_threshold=True,
        breakdown=ScoreBreakdown(
            ats_keyword_match=25,
            role_relevance=24,
            quantifiable_impact=18,
            factual_integrity=14,
            format_and_length=13,
        ),
        strengths=["Strong cloud architecture"],
    )
    markdown_text = (
        "# Mateo Pissarello\n"
        '<div class="headline">\nSenior Backend Engineer | Python & Cloud\n</div>\n'
        "## Profile\nBackend Engineer specialized in distributed systems.\n"
        "## Experience\n### RenderCloud\n"
    )
    report = TailoringReport(
        job=mock_job,
        final_markdown=markdown_text,
        final_evaluation=mock_eval,
        iterations=[],
        output_file_path=empty_outputs / "resume_RenderCloud_Senior_Backend_Engineer_20261117_193000.md",
        language="en",
    )

    with Session(test_engine, expire_on_commit=False) as session:
        persist_tailoring_report(
            report=report,
            filename="resume_RenderCloud_Senior_Backend_Engineer_20261117_193000.md",
            timestamp_raw="20261117_193000",
            session=session,
        )

    # Confirmar que NO hay ningún archivo físico en empty_outputs
    assert list(empty_outputs.glob("*.md")) == []

    def override_get_db():
        with Session(test_engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        # 1. El listado de historial debe devolver el CV desde la tabla GeneratedResume
        hist_res = client.get("/api/tailor/history")
        assert hist_res.status_code == 200
        items = hist_res.json()
        assert len(items) == 1
        assert items[0]["company"] == "RenderCloud"
        assert items[0]["ats_score"] == 94

        # 2. El detalle debe servirse íntegro desde la base de datos sin archivo en disco
        fname = items[0]["filename"]
        detail_res = client.get(f"/api/tailor/history/{fname}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["markdown"] == markdown_text
        assert detail["evaluation"]["total_score"] == 94


def test_cloud_sync_push_local_to_target_db_and_cli(tmp_path):
    src_db = tmp_path / "source_local.db"
    dst_db = tmp_path / "target_cloud.db"
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()

    # Poblar base de datos fuente
    src_engine = create_engine(f"sqlite:///{src_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(src_engine)
    with Session(src_engine, expire_on_commit=False) as s:
        s.add(PersonalInfo(full_name="Mateo Pissarello", headline="Backend & AI Engineer"))
        exp = WorkExperience(
            company="Blend360 Colombia",
            role="Backend Developer",
            location="Bogotá",
            start_date="Nov. 2024",
            end_date="Jan. 2026",
        )
        s.add(exp)
        s.commit()
        s.refresh(exp)
        s.add(
            WorkProject(
                work_experience_id=exp.id,
                name="Zammad on Kubernetes (EKS)",
                bullets=["Deployed Zammad on EKS using **AWS CDK** and **ArgoCD**."],
                technologies=["Kubernetes", "AWS CDK", "ArgoCD"],
            )
        )
        s.add(TrackedRepo(name="juanchito-assistant", is_active=True, priority=1, category="AI/ML"))
        s.add(SkillCategory(category="Languages", skills=["Python", "TypeScript"]))
        s.add(Certification(issuer="AWS", title="Solutions Architect Associate", issue_date="Apr. 2025"))
        s.commit()

    # Crear también un CV en outputs_dir para probar su ingesta y migración automática
    sample_md = outputs_dir / "resume_GitLab_Backend_Engineer_20261103_101241.md"
    sample_md.write_text(
        '# Mateo Pissarello\n<div class="headline">\nBackend Engineer\n</div>\n'
        "## Profile\nBuilding reliable distributed systems with Python and FastAPI across cloud environments.\n",
        encoding="utf-8",
    )

    target_url = f"sqlite:///{dst_db}"
    counts = push_local_to_target_db(
        target_url=target_url,
        source_db_path=src_db,
        outputs_dir=outputs_dir,
    )

    assert counts["personal"] == 1
    assert counts["experiences"] == 1
    assert counts["work_projects"] == 1
    assert counts["tracked_repos"] == 1
    assert counts["skills"] == 1
    assert counts["certifications"] == 1
    assert counts["generated_resumes"] == 1

    # Verificar idempotencia ejecutando el comando CLI 'juanchito db push' una segunda vez
    runner = CliRunner()
    res = runner.invoke(
        cli_app,
        [
            "db",
            "push",
            "--target-url",
            target_url,
            "--source-db",
            str(src_db),
            "--outputs-dir",
            str(outputs_dir),
        ],
    )
    assert res.exit_code == 0
    assert "Base de datos en la nube actualizada al 100%" in res.output

    # Comprobar que no se duplicaron registros en destino
    dst_engine = create_engine(target_url)
    with Session(dst_engine) as dst_sess:
        assert len(dst_sess.exec(select(WorkExperience)).all()) == 1
        assert len(dst_sess.exec(select(WorkProject)).all()) == 1
        assert len(dst_sess.exec(select(GeneratedResume)).all()) == 1
