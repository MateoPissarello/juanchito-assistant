import httpx
import pytest

from juanchito_assitant.ingest.github_client import GitHubClient, RepoContext


@pytest.mark.anyio
async def test_list_repos_authenticated_with_fork_filter():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/user/repos"
        assert request.url.params["visibility"] == "all"
        assert request.headers["Authorization"] == "Bearer mock_token"
        mock_data = [
            {
                "name": "goofish-scraping",
                "fork": False,
                "owner": {"login": "MateoPissarello"},
                "html_url": "https://github.com/MateoPissarello/goofish-scraping",
            },
            {
                "name": "forked-repo",
                "fork": True,
                "owner": {"login": "MateoPissarello"},
                "html_url": "https://github.com/MateoPissarello/forked-repo",
            },
            {
                "name": "ParcialCV3Final",
                "fork": False,
                "owner": {"login": "MateoPissarello"},
                "html_url": "https://github.com/MateoPissarello/ParcialCV3Final",
            },
        ]
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token="mock_token", transport=transport)
    repos = await client.list_repos(username="MateoPissarello", exclude_forks=True)

    assert len(repos) == 2
    names = [r["name"] for r in repos]
    assert "goofish-scraping" in names
    assert "ParcialCV3Final" in names
    assert "forked-repo" not in names


@pytest.mark.anyio
async def test_list_repos_unauthenticated():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/users/MateoPissarello/repos"
        mock_data = [
            {"name": "CanvaToPdf", "fork": False, "owner": {"login": "MateoPissarello"}},
        ]
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token="", transport=transport)
    repos = await client.list_repos(username="MateoPissarello")

    assert len(repos) == 1
    assert repos[0]["name"] == "CanvaToPdf"


@pytest.mark.anyio
async def test_inspect_repo_tree_readme_and_manifests():
    tree_payload = {
        "tree": [
            {"path": "README.md", "type": "blob", "size": 150},
            {"path": "pyproject.toml", "type": "blob", "size": 300},
            {"path": "src/main.py", "type": "blob", "size": 1200},
            {"path": "Dockerfile", "type": "blob", "size": 400},
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "git/trees/scraping-v2" in path:
            return httpx.Response(200, json=tree_payload)
        elif "contents/README.md" in path:
            return httpx.Response(200, text="# Goofish Scraping\nHerramienta de scraping asíncrona.")
        elif "contents/pyproject.toml" in path:
            return httpx.Response(
                200, text="[project]\nname = 'goofish-scraping'\ndependencies = ['playwright', 'httpx']"
            )
        elif "contents/Dockerfile" in path:
            return httpx.Response(200, text="FROM python:3.11-slim\nCMD ['python', 'src/main.py']")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token="mock_token", transport=transport)

    ctx: RepoContext = await client.inspect_repo(
        owner="MateoPissarello",
        repo_name="goofish-scraping",
        branch="scraping-v2",
        html_url="https://github.com/MateoPissarello/goofish-scraping",
        description="Scraper para Goofish",
    )

    assert ctx.repo_name == "goofish-scraping"
    assert ctx.branch == "scraping-v2"
    assert ctx.readme_filename == "README.md"
    assert ctx.readme_content is not None
    assert "Herramienta de scraping" in ctx.readme_content
    assert "pyproject.toml" in ctx.manifests
    assert "playwright" in ctx.manifests["pyproject.toml"]
    assert "Dockerfile" in ctx.manifests
    assert len(ctx.tree_paths) == 4
