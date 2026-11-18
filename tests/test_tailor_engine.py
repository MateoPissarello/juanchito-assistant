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


@pytest.mark.anyio
async def test_evaluator_deterministic_pre_audit_and_anti_hallucination_filter():
    session = get_test_db_session()
    matcher = MatcherAgent(session)

    job = JobRequirements(
        job_title="Senior Backend Engineer",
        must_have_skills=["Python", "FastAPI", "Snowflake"],
        nice_to_have_skills=["Docker"],
        core_responsibilities=["Build APIs"],
        ats_keywords=[],
        role_summary="Backend role",
    )
    matched_ctx = matcher.match(job)

    # El LLM evaluador intenta sugerir erróneamente agregar Snowflake (que el candidato NO tiene)
    mock_eval = {
        "choices": [
            {
                "message": {
                    "content": """{
                        "total_score": 78,
                        "meets_threshold": false,
                        "decision": "REWRITE",
                        "breakdown": {
                            "ats_keyword_match": 18,
                            "role_relevance": 22,
                            "quantifiable_impact": 14,
                            "factual_integrity": 12,
                            "format_and_length": 12
                        },
                        "strengths": ["Good Python foundation"],
                        "critical_weaknesses": [],
                        "actionable_improvements": [
                            "Integrate Snowflake into bullet points to substantiate data warehousing skills.",
                            "Quantify API latency improvements with percentages."
                        ]
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

    # El CV generado menciona Python pero olvidó mencionar FastAPI y Docker (que sí tiene en SQLite)
    resume_md = """# Mateo Pissarello
## Profile
Backend developer using Python.
## Experience
- **AICodeFixer**
    - Built code remediation tool reducing bugs by **40%** using **Python**.
"""
    res = await evaluator.evaluate(resume_md, job, language="en", matched_ctx=matched_ctx)

    # 1. Clasificación determinista de skills
    assert "python" in [s.lower() for s in res.matched_job_skills]
    assert "fastapi" in [s.lower() for s in res.missing_owned_skills]
    assert "snowflake" in [s.lower() for s in res.unowned_job_skills]

    # 2. La sugerencia tóxica de agregar Snowflake fue filtrada de actionable_improvements
    assert not any("snowflake" in imp.lower() for imp in res.actionable_improvements)

    # 3. Se inyectó automáticamente la instrucción para incluir FastAPI y Docker (que sí posee en SQLite)
    assert any("fastapi" in imp.lower() for imp in res.actionable_improvements)

    # 4. La brecha real de Snowflake se reporta transparentemente en critical_weaknesses
    assert any("snowflake" in w.lower() for w in res.critical_weaknesses)


@pytest.mark.anyio
async def test_tailoring_engine_stateful_revision_and_best_of_n():
    session = get_test_db_session()

    analyzer = JobAnalyzerAgent(provider="openrouter", api_key="k")
    analyzer.analyze_job = AsyncMock(
        return_value=JobRequirements(
            job_title="Backend Developer",
            company_name="BestOfNCorp",
            must_have_skills=["Python", "FastAPI", "Snowflake"],
            role_summary="Backend job",
        )
    )
    matcher = MatcherAgent(session)

    writer = WriterAgent(provider="openrouter", api_key="k")
    captured_calls: list[dict] = []

    async def fake_write_resume(ctx, feedback=None, language="en", previous_draft=None):
        captured_calls.append({"feedback": feedback, "previous_draft": previous_draft})
        if previous_draft is None:
            writer.last_guardrail_alerts = ["Alucinación bloqueada: 'snowflake'"]
            return "# Draft Round 1 (Score 83)"
        else:
            writer.last_guardrail_alerts = []
            return "# Draft Round 2 (Score 77 - Regressed)"

    writer.write_resume = fake_write_resume

    evaluator = EvaluatorAgent(api_key="k")
    eval_round = 0

    async def fake_evaluate(markdown, job, language="en", matched_ctx=None):
        nonlocal eval_round
        eval_round += 1
        if eval_round == 1:
            return EvaluationResult(
                total_score=83,
                meets_threshold=False,
                decision="REWRITE",
                breakdown=ScoreBreakdown(
                    ats_keyword_match=21,
                    role_relevance=22,
                    quantifiable_impact=16,
                    factual_integrity=12,
                    format_and_length=12,
                ),
                actionable_improvements=["Include FastAPI in summary"],
                unowned_job_skills=["Snowflake"],
            )
        return EvaluationResult(
            total_score=77,
            meets_threshold=False,
            decision="REWRITE",
            breakdown=ScoreBreakdown(
                ats_keyword_match=19,
                role_relevance=20,
                quantifiable_impact=14,
                factual_integrity=12,
                format_and_length=12,
            ),
            actionable_improvements=[],
            unowned_job_skills=["Snowflake"],
        )

    evaluator.evaluate = fake_evaluate

    engine = TailoringEngine(
        session=session,
        job_analyzer=analyzer,
        matcher=matcher,
        writer=writer,
        evaluator=evaluator,
    )

    report = await engine.run("Job description", max_iterations=2)

    # 1. Verificar que la Ronda 2 recibió previous_draft de la Ronda 1 y las alertas del guardrail
    assert len(captured_calls) == 2
    assert captured_calls[0]["previous_draft"] is None
    assert captured_calls[1]["previous_draft"] == "# Draft Round 1 (Score 83)"
    assert any("ALERTA DE GUARDRAIL" in f for f in captured_calls[1]["feedback"])
    assert any("PROHIBIDO inventar" in f and "Snowflake" in f for f in captured_calls[1]["feedback"])

    # 2. Verificar selección Best-of-N: como Ronda 1 (83) > Ronda 2 (77), el reporte final conserva Ronda 1
    assert report.final_evaluation.total_score == 83
    assert report.final_markdown == "# Draft Round 1 (Score 83)"
    assert report.iterations[0].guardrail_alerts == ["Alucinación bloqueada: 'snowflake'"]


@pytest.mark.anyio
async def test_job_analyzer_linkedin_url_metadata_and_company_fallback():
    sample_html = """
    <html>
      <head>
        <title>Backend Engineer (Python),AI Engineering: Agent Foundations at GitLab — Canada | LinkedIn Jobs</title>
        <meta property="og:title" content="Backend Engineer (Python),AI Engineering: Agent Foundations at GitLab — Canada | LinkedIn Jobs">
      </head>
      <body>
        <h1>Backend Engineer (Python),AI Engineering: Agent Foundations</h1>
        <a class="topcard__org-name-link" href="https://www.linkedin.com/company/gitlab-com">GitLab</a>
        <div class="show-more-less-html__markup">
          Most of your work will be backend engineering in Python using LangGraph and FastAPI.
        </div>
      </body>
    </html>
    """
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        requested_urls.append(url_str)
        if "linkedin.com" in url_str:
            return httpx.Response(200, text=sample_html)
        # Simular que el LLM devuelve company_name: null para probar también el fallback determinista
        return httpx.Response(
            200,
            json={
                "model": "deepseek/deepseek-chat",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": """{
                                "job_title": "Backend Engineer (Python), AI Engineering: Agent Foundations",
                                "company_name": null,
                                "seniority_level": "Mid-Senior",
                                "must_have_skills": ["Python", "LangGraph", "FastAPI"],
                                "nice_to_have_skills": [],
                                "core_responsibilities": ["Build agentic AI features"],
                                "ats_keywords": ["Python", "LangGraph"],
                                "role_summary": "Build agentic AI foundations at GitLab."
                            }""",
                        }
                    }
                ],
            },
        )

    agent = JobAnalyzerAgent(
        provider="openrouter",
        api_key="mock_key",
        http_transport=httpx.MockTransport(handler),
    )

    res = await agent.analyze_job("https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4474179582")
    assert requested_urls[0] == "https://www.linkedin.com/jobs/view/4474179582/"
    assert res.company_name == "GitLab"
    assert "LangGraph" in res.must_have_skills

