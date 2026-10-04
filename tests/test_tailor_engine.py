from unittest.mock import AsyncMock
import httpx
import pytest
from sqlmodel import Session, SQLModel, create_engine

from juanchito_assitant.agents.cv_writer import WriterAgent
from juanchito_assitant.agents.evaluator import EvaluatorAgent
from juanchito_assitant.agents.job_analyzer import JobAnalyzerAgent
from juanchito_assitant.agents.matcher import MatcherAgent
from juanchito_assitant.models.evaluation import EvaluationResult, ScoreBreakdown
from juanchito_assitant.models.job import JobRequirements
from juanchito_assitant.models.profile import (
    Certification,
    PersonalInfo,
    PersonalProject,
    SkillCategory,
    WorkExperience,
    WorkProject,
)
from juanchito_assitant.tailor_engine import TailoringEngine


def get_test_db_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    # Seed data
    p = PersonalInfo(full_name="Mateo Pissarello", email="test@example.com")
    session.add(p)

    w = WorkExperience(company="Blend360 Colombia", role="Trainee", location="Bogotá", start_date="Nov. 2024")
    session.add(w)
    session.flush()

    wp = WorkProject(
        work_experience_id=w.id,
        name="AICodeFixer",
        bullets=["Built automated code remediation with **FastAPI**."],
        technologies=["FastAPI", "Python", "Docker"],
    )
    session.add(wp)

    repo = PersonalProject(
        name="goofish-scraping",
        repo_url="https://github.com/MateoPissarello/goofish-scraping",
        technologies=["Python", "Playwright", "FastAPI"],
        bullets=["Scraping microservices."],
    )
    session.add(repo)

    cert = Certification(issuer="AWS", title="AWS Certified Solutions Architect", issue_date="2025")
    session.add(cert)

    cat = SkillCategory(category="Backend", skills=["Python", "FastAPI"])
    session.add(cat)

    session.commit()
    return session


@pytest.mark.anyio
async def test_job_analyzer_mock():
    mock_resp = {
        "choices": [
            {
                "message": {
                    "content": """{
                        "job_title": "Backend Developer",
                        "company_name": "Tech Corp",
                        "seniority_level": "Mid",
                        "must_have_skills": ["Python", "FastAPI"],
                        "nice_to_have_skills": ["Docker"],
                        "core_responsibilities": ["Develop APIs"],
                        "ats_keywords": ["Microservices", "REST"],
                        "role_summary": "Develop modern backend systems."
                    }"""
                }
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_resp)

    agent = JobAnalyzerAgent(
        provider="openrouter",
        api_key="mock_key",
        http_transport=httpx.MockTransport(handler),
    )
    res = await agent.analyze_job("Job description for Backend Developer with Python and FastAPI.")
    assert res.job_title == "Backend Developer"
    assert "Python" in res.must_have_skills


def test_matcher_scoring():
    session = get_test_db_session()
    matcher = MatcherAgent(session)

    job = JobRequirements(
        job_title="Python Backend Engineer",
        must_have_skills=["Python", "FastAPI"],
        nice_to_have_skills=["Docker"],
        core_responsibilities=["APIs"],
        ats_keywords=["Microservices"],
        role_summary="Backend role",
    )

    ctx = matcher.match(job)
    assert len(ctx.work_matches) >= 1
    assert ctx.work_matches[0].project_name == "AICodeFixer"
    assert ctx.work_matches[0].match_score > 0
    assert len(ctx.github_matches) >= 1
    assert ctx.github_matches[0].name == "goofish-scraping"


@pytest.mark.anyio
async def test_evaluator_jev_mock():
    mock_eval = {
        "choices": [
            {
                "message": {
                    "content": """{
                        "total_score": 92,
                        "meets_threshold": true,
                        "decision": "APPROVE",
                        "breakdown": {
                            "ats_keyword_match": 24,
                            "role_relevance": 24,
                            "quantifiable_impact": 18,
                            "factual_integrity": 13,
                            "format_and_length": 13
                        },
                        "strengths": ["Strong FastAPI coverage"],
                        "critical_weaknesses": [],
                        "actionable_improvements": []
                    }"""
                }
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_eval)

    evaluator = EvaluatorAgent(
        api_key="mock_key",
        http_transport=httpx.MockTransport(handler),
    )

    job = JobRequirements(
        job_title="Backend Developer",
        must_have_skills=["Python"],
        nice_to_have_skills=[],
        core_responsibilities=[],
        ats_keywords=[],
        role_summary="Backend role",
    )

    res = await evaluator.evaluate("# Resume Markdown", job)
    assert res.total_score == 92
    assert res.meets_threshold is True
    assert res.decision == "APPROVE"


@pytest.mark.anyio
async def test_tailoring_engine_full_loop(tmp_path, monkeypatch):
    session = get_test_db_session()

    # Mock Job Analyzer
    analyzer = JobAnalyzerAgent(provider="openrouter", api_key="k")
    analyzer.analyze_job = AsyncMock(
        return_value=JobRequirements(
            job_title="Backend Developer",
            company_name="Acme",
            must_have_skills=["Python"],
            role_summary="Awesome job",
        )
    )

    # Mock Matcher
    matcher = MatcherAgent(session)

    # Mock Writer
    writer = WriterAgent(provider="openrouter", api_key="k")
    writer.write_resume = AsyncMock(return_value="# Generated CV Markdown")

    # Mock Evaluator
    evaluator = EvaluatorAgent(api_key="k")
    evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            total_score=90,
            meets_threshold=True,
            decision="APPROVE",
            breakdown=ScoreBreakdown(
                ats_keyword_match=23,
                role_relevance=23,
                quantifiable_impact=18,
                factual_integrity=13,
                format_and_length=13,
            ),
        )
    )

    engine = TailoringEngine(
        session=session,
        job_analyzer=analyzer,
        matcher=matcher,
        writer=writer,
        evaluator=evaluator,
    )

    report = await engine.run("Backend Developer job description", max_iterations=2)
    assert report.job.company_name == "Acme"
    assert report.final_evaluation.total_score == 90
    assert len(report.iterations) == 1
    assert report.output_file_path.exists()
