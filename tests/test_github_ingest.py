from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from juanchito_assitant.agents.repo_analyzer import RepoAnalysisResult, RepoAnalyzer
from juanchito_assitant.ingest.github_client import GitHubClient, RepoContext
from juanchito_assitant.ingest.github_ingest import GitHubIngestService
from juanchito_assitant.models.profile import PersonalProject, TrackedRepo


@pytest.mark.anyio
async def test_sync_repo_idempotent_upsert_and_cache_invalidation():
    # Base de datos SQLite en memoria
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    # Mocks
    mock_gh = MagicMock(spec=GitHubClient)
    mock_gh.inspect_repo = AsyncMock(
        return_value=RepoContext(
            repo_name="CanvaToPdf",
            owner="MateoPissarello",
            branch="main",
            html_url="https://github.com/MateoPissarello/CanvaToPdf",
            description="Convert Canva to PDF",
        )
    )

    mock_analyzer = MagicMock(spec=RepoAnalyzer)
    mock_analyzer.analyze = AsyncMock(
        return_value=RepoAnalysisResult(
            has_adequate_readme=True,
            summary="Python CLI tool to batch convert Canva presentation links into merged PDFs.",
            bullets=[
                "Automated PDF export workflow using **Python** and **Playwright**, saving **4+ hours weekly**.",
                "Engineered headless browser pipeline with retry logic achieving **99.5% download reliability**."
            ],
            technologies=["Python", "Playwright", "PDF"],
            suggested_readme=None,
        )
    )

    service = GitHubIngestService(
        github_client=mock_gh,
        analyzer=mock_analyzer,
        engine=engine,
    )

    repo_data = {
        "name": "CanvaToPdf",
        "owner": {"login": "MateoPissarello"},
        "html_url": "https://github.com/MateoPissarello/CanvaToPdf",
        "description": "Convert Canva to PDF",
        "default_branch": "main",
        "pushed_at": "2026-10-04T12:00:00Z",
    }

    # 1. Primera inserción: debe llamar a la IA
    p1, was_updated = await service.sync_repo(repo_data)
    assert p1.name == "CanvaToPdf"
    assert was_updated is True
    assert p1.last_pushed_at == "2026-10-04T12:00:00Z"
    assert mock_analyzer.analyze.call_count == 1

    # 2. Segunda ejecución sin cambios (mismo pushed_at): NO debe llamar a la IA
    p2, was_updated_2 = await service.sync_repo(repo_data)
    assert p2.name == "CanvaToPdf"
    assert was_updated_2 is False  # Omitido / Cache hit!
    assert mock_analyzer.analyze.call_count == 1  # No se volvió a llamar al LLM!

    # 3. Tercera ejecución con nuevo commit (pushed_at cambia): SÍ debe llamar a la IA
    repo_data_updated = dict(repo_data, pushed_at="2026-10-04T14:30:00Z")
    mock_analyzer.analyze = AsyncMock(
        return_value=RepoAnalysisResult(
            has_adequate_readme=True,
            summary="Updated Canva tool with new features.",
            bullets=["Fresh bullet with **Playwright**."],
            technologies=["Python", "Playwright"],
            suggested_readme=None,
        )
    )
    p3, was_updated_3 = await service.sync_repo(repo_data_updated)
    assert p3.name == "CanvaToPdf"
    assert was_updated_3 is True
    assert p3.last_pushed_at == "2026-10-04T14:30:00Z"
    assert p3.description == "Updated Canva tool with new features."


@pytest.mark.anyio
async def test_sync_all_with_branch_override():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    mock_gh = MagicMock(spec=GitHubClient)
    mock_gh.list_repos = AsyncMock(
        return_value=[
            {
                "name": "goofish-scraping",
                "owner": {"login": "MateoPissarello"},
                "html_url": "https://github.com/MateoPissarello/goofish-scraping",
                "default_branch": "main",
                "pushed_at": "2026-09-01T10:00:00Z",
            },
            {
                "name": "ignored-repo",
                "owner": {"login": "MateoPissarello"},
                "html_url": "https://github.com/MateoPissarello/ignored-repo",
                "default_branch": "main",
                "pushed_at": "2026-09-01T10:00:00Z",
            },
        ]
    )
    mock_gh.inspect_repo = AsyncMock(
        return_value=RepoContext(
            repo_name="goofish-scraping",
            owner="MateoPissarello",
            branch="scraping-v2",
        )
    )

    mock_analyzer = MagicMock(spec=RepoAnalyzer)
    mock_analyzer.analyze = AsyncMock(
        return_value=RepoAnalysisResult(
            has_adequate_readme=False,
            summary="Scraper de Goofish",
            bullets=["Extracted product catalogs using **httpx** and **FastAPI**."],
            technologies=["Python", "httpx"],
            suggested_readme="# Goofish Scraping",
        )
    )

    overrides = {
        "goofish-scraping": {"branch": "scraping-v2"},
        "ignored-repo": {"include": False},
    }

    service = GitHubIngestService(
        github_client=mock_gh,
        analyzer=mock_analyzer,
        engine=engine,
        overrides=overrides,
    )

    results = await service.sync_all(username="MateoPissarello")
    assert len(results) == 1
    project, was_updated = results[0]
    assert project.name == "goofish-scraping"
    assert project.branch == "scraping-v2"
    assert project.has_readme is False
    assert project.suggested_readme == "# Goofish Scraping"


@pytest.mark.anyio
async def test_sync_all_resolves_targets_from_tracked_repo_table():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    # Insertar repositorios configurados en TrackedRepo
    with Session(engine) as session:
        session.add(TrackedRepo(name="tracked-repo-1", branch="v2", is_active=True))
        session.add(TrackedRepo(name="tracked-repo-2", is_active=False))  # Inactivo, no debe sincronizar
        session.commit()

    mock_gh = MagicMock(spec=GitHubClient)
    mock_gh.list_repos = AsyncMock(
        return_value=[
            {"name": "tracked-repo-1", "owner": {"login": "MateoPissarello"}, "default_branch": "main"},
            {"name": "tracked-repo-2", "owner": {"login": "MateoPissarello"}, "default_branch": "main"},
            {"name": "other-untracked", "owner": {"login": "MateoPissarello"}, "default_branch": "main"},
        ]
    )
    mock_gh.inspect_repo = AsyncMock(
        return_value=RepoContext(
            repo_name="tracked-repo-1",
            owner="MateoPissarello",
            branch="v2",
        )
    )

    mock_analyzer = MagicMock(spec=RepoAnalyzer)
    mock_analyzer.analyze = AsyncMock(
        return_value=RepoAnalysisResult(
            has_adequate_readme=True,
            summary="Tracked repo summary",
            bullets=["Bullet 1"],
            technologies=["Python"],
            suggested_readme=None,
        )
    )

    service = GitHubIngestService(
        github_client=mock_gh,
        analyzer=mock_analyzer,
        engine=engine,
        # overrides=None -> debe consultar TrackedRepo de SQLite
    )

    results = await service.sync_all(username="MateoPissarello")
    assert len(results) == 1
    project, was_updated = results[0]
    assert project.name == "tracked-repo-1"
    assert project.branch == "v2"
    assert was_updated is True


@pytest.mark.anyio
async def test_sync_all_on_status_reporting():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    mock_gh = MagicMock(spec=GitHubClient)
    mock_gh.list_repos = AsyncMock(
        return_value=[
            {"name": "repo-a", "owner": {"login": "MateoPissarello"}, "default_branch": "main", "pushed_at": "2026-01-01T00:00:00Z"},
        ]
    )
    mock_gh.inspect_repo = AsyncMock(
        return_value=RepoContext(repo_name="repo-a", owner="MateoPissarello", branch="main")
    )

    mock_analyzer = MagicMock(spec=RepoAnalyzer)
    mock_analyzer.analyze = AsyncMock(
        return_value=RepoAnalysisResult(
            has_adequate_readme=True,
            summary="Repo A summary",
            bullets=["Bullet 1"],
            technologies=["Python"],
            suggested_readme=None,
        )
    )

    service = GitHubIngestService(
        github_client=mock_gh,
        analyzer=mock_analyzer,
        engine=engine,
        overrides={"repo-a": {"include": True}},
    )

    events = []
    def tracker(repo, status, msg):
        events.append((repo, status, msg))

    await service.sync_all(username="MateoPissarello", repo_names=["repo-a", "repo-missing"], on_status=tracker)

    # Debe reportar not_found para repo-missing
    assert any(e[0] == "repo-missing" and e[1] == "not_found" for e in events)
    # Debe reportar analyzing y completed para repo-a
    assert any(e[0] == "repo-a" and e[1] == "analyzing" for e in events)
    assert any(e[0] == "repo-a" and e[1] == "completed" for e in events)


