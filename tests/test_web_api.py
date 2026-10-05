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
