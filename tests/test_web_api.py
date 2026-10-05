import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from juanchito_assitant.db.database import get_session
from juanchito_assitant.web.api import get_db
from juanchito_assitant.web.app import create_app
import juanchito_assitant.models.profile  # noqa: F401


@pytest.fixture(name="client")
def client_fixture(tmp_path):
    test_db = tmp_path / "test_web.db"
    test_engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)

    def override_get_db():
        with Session(test_engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_profile_empty_then_update_personal(client):
    res = client.get("/api/profile")
    assert res.status_code == 200
    data = res.json()
    assert "personal" in data
    assert "experiences" in data
    assert "tracked_repos" in data

    # Update personal info
    update_payload = {
        "full_name": "Mateo Pissarello Dev",
        "headline": "Senior Distributed Systems Engineer",
        "location": "Bogotá, Colombia",
        "timezone": "GMT-05",
        "email": "mateo@example.com",
        "phone": "+57 300 000 0000",
        "linkedin": "mateo-pissarello",
        "github": "MateoPissarello",
        "profile_summary": "Expert in cloud architecture.",
    }
    update_res = client.put("/api/profile/personal", json=update_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["full_name"] == "Mateo Pissarello Dev"
    assert updated_data["headline"] == "Senior Distributed Systems Engineer"


def test_work_experience_and_projects_crud(client):
    # Create Experience
    exp_payload = {
        "company": "Tech Corp",
        "role": "Lead Architect",
        "location": "Remote",
        "start_date": "Jan. 2025",
        "end_date": "Present",
        "is_current": True,
        "order_index": 1,
    }
    create_exp_res = client.post("/api/profile/experiences", json=exp_payload)
    assert create_exp_res.status_code == 201
    exp = create_exp_res.json()
    exp_id = exp["id"]

    # Create WorkProject under this experience
    proj_payload = {
        "work_experience_id": exp_id,
        "name": "CloudMigration",
        "bullets": ["Migrated monolith to microservices on AWS EKS with **99.99%** uptime."],
        "technologies": ["AWS", "Docker", "Kubernetes", "Python"],
        "priority_weight": 2,
    }
    create_proj_res = client.post("/api/profile/projects", json=proj_payload)
    assert create_proj_res.status_code == 201
    proj = create_proj_res.json()
    proj_id = proj["id"]

    # Update project
    update_proj_res = client.put(
        f"/api/profile/projects/{proj_id}",
        json={"name": "CloudMigrationV2", "priority_weight": 3},
    )
    assert update_proj_res.status_code == 200
    assert update_proj_res.json()["name"] == "CloudMigrationV2"

    # Verify nested in get profile
    profile_res = client.get("/api/profile")
    profile_data = profile_res.json()
    assert len(profile_data["experiences"]) == 1
    assert len(profile_data["experiences"][0]["projects"]) == 1
    assert profile_data["experiences"][0]["projects"][0]["name"] == "CloudMigrationV2"

    # Delete project
    del_proj = client.delete(f"/api/profile/projects/{proj_id}")
    assert del_proj.status_code == 200

    # Delete experience
    del_exp = client.delete(f"/api/profile/experiences/{exp_id}")
    assert del_exp.status_code == 200


def test_tracked_repos_crud(client):
    # Add repo
    repo_payload = {
        "name": "my-cool-service",
        "branch": "develop",
        "is_active": True,
        "priority": 1,
        "category": "Backend",
        "notes": "Core API",
    }
    create_res = client.post("/api/repos", json=repo_payload)
    assert create_res.status_code == 201
    repo = create_res.json()
    repo_id = repo["id"]

    # Toggle
    toggle_res = client.patch(f"/api/repos/{repo_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # Toggle back
    toggle_res2 = client.patch(f"/api/repos/{repo_id}/toggle")
    assert toggle_res2.status_code == 200
    assert toggle_res2.json()["is_active"] is True

    # List
    list_res = client.get("/api/repos")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Delete
    del_res = client.delete(f"/api/repos/{repo_id}")
    assert del_res.status_code == 200


def test_skills_and_certifications_crud(client):
    # Add skill category
    skill_payload = {
        "category": "Cloud & DevOps",
        "skills": ["AWS", "Terraform", "Kubernetes"],
    }
    cat_res = client.post("/api/profile/skills", json=skill_payload)
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    # Update skills
    update_cat = client.put(f"/api/profile/skills/{cat_id}", json={"skills": ["AWS", "Terraform", "Docker"]})
    assert update_cat.status_code == 200
    assert "Docker" in update_cat.json()["skills"]

    # Add certification
    cert_payload = {
        "issuer": "Amazon Web Services",
        "title": "Solutions Architect Associate",
        "issue_date": "2025",
    }
    cert_res = client.post("/api/profile/certifications", json=cert_payload)
    assert cert_res.status_code == 201
    cert_id = cert_res.json()["id"]

    # Delete certification
    del_cert = client.delete(f"/api/profile/certifications/{cert_id}")
    assert del_cert.status_code == 200

    # Delete skill category
    del_skill = client.delete(f"/api/profile/skills/{cat_id}")
    assert del_skill.status_code == 200


def test_tailor_stream_empty_input_error(client):
    res = client.post("/api/tailor/stream", json={"job_input": "   "})
    assert res.status_code == 400
    assert "Debe ingresar" in res.json()["detail"]


def test_tailor_stream_success(client, tmp_path):
    from unittest.mock import patch
    from juanchito_assitant.models.evaluation import EvaluationResult, ScoreBreakdown
    from juanchito_assitant.models.job import JobRequirements
    from juanchito_assitant.tailor_engine import TailoringReport

    mock_job = JobRequirements(
        job_title="Backend Engineer",
        company_name="Acme Corp",
        role_summary="Building APIs",
        must_have_skills=["Python"],
    )
    mock_eval = EvaluationResult(
        total_score=92,
        decision="APPROVE",
        meets_threshold=True,
        breakdown=ScoreBreakdown(
            ats_keyword_match=25,
            role_relevance=25,
            quantifiable_impact=18,
            factual_integrity=12,
            format_and_length=12,
        ),
    )
    mock_report = TailoringReport(
        job=mock_job,
        final_markdown="# Mateo Pissarello\n## Profile\nEngineer",
        final_evaluation=mock_eval,
        iterations=[],
        output_file_path=tmp_path / "resume.md",
    )

    async def fake_run(self, job_input, max_iterations=2, language="en", on_progress=None):
        if on_progress:
            await on_progress("analyzing", {"message": f"Analizando vacante ({language})..."})
            await on_progress("completed", {"report": mock_report.model_dump(mode="json")})
        return mock_report

    with patch("juanchito_assitant.web.api.TailoringEngine.run", new=fake_run):
        res = client.post(
            "/api/tailor/stream",
            json={"job_input": "Backend Engineer at Acme", "language": "es"},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        body = res.text
        assert "data: " in body
        assert "es" in body
        assert "completed" in body


def test_tailor_stream_max_iterations_validation(client):
    # max_iterations=5 is allowed
    res_ok = client.post(
        "/api/tailor/stream",
        json={"job_input": "   ", "max_iterations": 5},
    )
    assert res_ok.status_code == 400  # Empty input validation

    # max_iterations=6 exceeds the upper limit le=5
    res_invalid = client.post(
        "/api/tailor/stream",
        json={"job_input": "Backend Engineer", "max_iterations": 6},
    )
    assert res_invalid.status_code == 422


def test_get_resume_history_and_detail(client, tmp_path, monkeypatch):
    mock_outputs = tmp_path / "outputs"
    mock_outputs.mkdir()

    # Stub file (< 100 bytes) should be ignored
    stub_file = mock_outputs / "resume_Acme_Dev_20261001_000000.md"
    stub_file.write_text("# Stub", encoding="utf-8")

    # Valid file in Spanish
    es_content = """# Mateo Pissarello
<div class="headline">
Senior Cloud Architect | AWS & Kubernetes
</div>
<div class="section headerInfo">
- Bogotá, Colombia
</div>

## Perfil Profesional
Ingeniero de software con más de 4 años de experiencia diseñando arquitecturas en la nube.

## Experiencia Laboral
### Senior Engineer
"""
    es_file = mock_outputs / "resume_Nubank_Senior_Backend_Engineer_20261004_181458.md"
    es_file.write_text(es_content, encoding="utf-8")

    # Valid file in English with companion JSON
    en_content = """# Mateo Pissarello
<div class="headline">
AI Engineer & Full-Stack Developer
</div>

## Profile
Experienced AI engineer building LLM applications and microservices with FastAPI and Docker.

## Experience
### AI Developer
"""
    en_file = mock_outputs / "resume_Atoms_AI_Engineer_20261005_101908.md"
    en_file.write_text(en_content, encoding="utf-8")

    # Add companion JSON for Atoms with ATS score = 92
    en_json = mock_outputs / "resume_Atoms_AI_Engineer_20261005_101908.json"
    en_json_data = {
        "final_evaluation": {
            "total_score": 92,
            "meets_threshold": True,
            "decision": "APPROVE",
            "breakdown": {
                "ats_keyword_match": 24,
                "role_relevance": 25,
                "quantifiable_impact": 18,
                "factual_integrity": 12,
                "format_and_length": 13,
            },
            "strengths": ["Great AWS coverage"],
            "critical_weaknesses": [],
            "actionable_improvements": [],
        }
    }
    en_json.write_text(json.dumps(en_json_data), encoding="utf-8")

    monkeypatch.setattr("juanchito_assitant.web.api.OUTPUTS_DIR", mock_outputs)

    # 1. Test GET /api/tailor/history
    res = client.get("/api/tailor/history")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2

    # Atoms has ats_score = 92
    assert items[0]["company"] == "Atoms"
    assert items[0]["ats_score"] == 92
    assert items[0]["ats_decision"] == "APPROVE"

    # Nubank has no JSON, so ats_score is None
    assert items[1]["company"] == "Nubank"
    assert items[1]["ats_score"] is None

    # 2. Test GET /api/tailor/history/{filename}
    detail_res = client.get(f"/api/tailor/history/{items[0]['filename']}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["company"] == "Atoms"
    assert detail["markdown"] == en_content
    assert detail["evaluation"] is not None
    assert detail["evaluation"]["total_score"] == 92

    # 3. Test 404 for non-existent file
    not_found_res = client.get("/api/tailor/history/resume_NonExistent_20261001_000000.md")
    assert not_found_res.status_code == 404

    # 4. Test 400 for path traversal or invalid filename
    bad_req_res = client.get("/api/tailor/history/../secret.txt")
    assert bad_req_res.status_code in (400, 404)

    # 5. Test POST /api/tailor/history/{filename}/audit (on-demand audit)
    from unittest.mock import patch
    from juanchito_assitant.models.evaluation import EvaluationResult, ScoreBreakdown

    mock_eval = EvaluationResult(
        total_score=88,
        meets_threshold=True,
        decision="APPROVE",
        breakdown=ScoreBreakdown(
            ats_keyword_match=23,
            role_relevance=24,
            quantifiable_impact=16,
            factual_integrity=11,
            format_and_length=14,
        ),
        strengths=["Strong backend skills"],
        critical_weaknesses=[],
        actionable_improvements=[],
    )

    async def fake_evaluate(self, job, resume_markdown, language="en"):
        return mock_eval

    with patch("juanchito_assitant.web.api.EvaluatorAgent.evaluate", new=fake_evaluate):
        audit_res = client.post(f"/api/tailor/history/{items[1]['filename']}/audit")
        assert audit_res.status_code == 200
        audited_data = audit_res.json()
        assert audited_data["ats_score"] == 88
        assert audited_data["ats_decision"] == "APPROVE"
        assert audited_data["evaluation"]["total_score"] == 88

        # Verify JSON file was created on disk
        created_json = mock_outputs / (items[1]["filename"].replace(".md", ".json"))
        assert created_json.is_file()





