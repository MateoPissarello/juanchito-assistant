from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest

from juanchito_assitant.agents.repo_analyzer import RepoAnalysisResult, RepoAnalyzer
from juanchito_assitant.ingest.github_client import RepoContext


def test_build_prompt_structure():
    analyzer = RepoAnalyzer(provider="openrouter", api_key="mock_key")
    ctx = RepoContext(
        repo_name="ParcialCV3Final",
        owner="MateoPissarello",
        branch="main",
        html_url="https://github.com/MateoPissarello/ParcialCV3Final",
        description="Computer Vision Project",
        tree_paths=["src/classifier.py", "requirements.txt", "model.pt"],
        readme_filename=None,
        readme_content=None,
        manifests={"requirements.txt": "torch>=2.0.0\nopencv-python>=4.8.0"},
    )

    prompt = analyzer._build_prompt(ctx)
    assert "ParcialCV3Final" in prompt
    assert "requirements.txt" in prompt
    assert "torch>=2.0.0" in prompt
    assert "src/classifier.py" in prompt
    assert "No README file found" in prompt


@pytest.mark.anyio
async def test_analyze_with_mocked_openrouter():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer mock_openrouter_key"
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": """{
                            "has_adequate_readme": false,
                            "summary": "Deep learning image classifier using PyTorch.",
                            "bullets": [
                                "Built an automated CNN pipeline using **PyTorch** and **OpenCV**, reaching **91% accuracy**.",
                                "Optimized inference throughput by **40%** with batch processing."
                            ],
                            "technologies": ["Python", "PyTorch", "OpenCV"],
                            "suggested_readme": "# ParcialCV3Final\\n\\nComputer vision model."
                        }"""
                    }
                }
            ]
        }
        return httpx.Response(200, json=mock_response)

    transport = httpx.MockTransport(handler)
    analyzer = RepoAnalyzer(
        provider="openrouter",
        api_key="mock_openrouter_key",
        model="google/gemini-2.5-flash",
        http_transport=transport,
    )

    ctx = RepoContext(
        repo_name="ParcialCV3Final",
        owner="MateoPissarello",
        tree_paths=["src/classifier.py", "requirements.txt"],
        manifests={"requirements.txt": "torch>=2.0.0"},
    )

    result = await analyzer.analyze(ctx)
    assert isinstance(result, RepoAnalysisResult)
    assert result.has_adequate_readme is False
    assert len(result.bullets) == 2
    assert "PyTorch" in result.technologies
    assert result.suggested_readme is not None


@pytest.mark.anyio
async def test_analyze_with_mocked_gemini():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """{
        "has_adequate_readme": false,
        "summary": "Deep learning-based computer vision classifier built with PyTorch and OpenCV.",
        "bullets": [
            "Developed an automated image classification pipeline using **PyTorch** and **OpenCV**, achieving **92% validation accuracy**.",
            "Architected custom CNN feature extractors reducing inference latency by **35%** on edge devices."
        ],
        "technologies": ["Python", "PyTorch", "OpenCV", "Deep Learning", "CNN"],
        "suggested_readme": "# ParcialCV3Final\\n\\nComputer Vision Classifier built with PyTorch."
    }"""
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    analyzer = RepoAnalyzer(provider="gemini", client=mock_client)
    ctx = RepoContext(
        repo_name="ParcialCV3Final",
        owner="MateoPissarello",
        tree_paths=["src/classifier.py", "requirements.txt"],
        manifests={"requirements.txt": "torch>=2.0.0\nopencv-python"},
    )

    result = await analyzer.analyze(ctx)

    assert isinstance(result, RepoAnalysisResult)
    assert result.has_adequate_readme is False
    assert len(result.bullets) == 2
    assert "PyTorch" in result.technologies
    assert result.suggested_readme is not None


@pytest.mark.anyio
async def test_analyze_missing_api_key_raises():
    analyzer = RepoAnalyzer(provider="none", api_key="", client=None)
    ctx = RepoContext(repo_name="test", owner="test")
    with pytest.raises(ValueError, match="No se encontró un proveedor de IA configurado"):
        await analyzer.analyze(ctx)


def test_clean_and_parse_llm_json_robustness():
    from juanchito_assitant.agents.repo_analyzer import _clean_and_parse_llm_json

    # 1. Caso con clave unificada ("summary: <texto>") y markdown fences
    malformed_1 = """```json
    {
      "has_adequate_readme": false,
      "summary: The cinema backend service manages ticketing, scheduling, and user auth.",
      "bullets": [
        "Built REST APIs using **FastAPI**.",
        "Containerized with **Docker**."
      ],
      "technologies": ["Python", "FastAPI", "Docker"],
      "suggested_readme": "# Cinema Service"
    }
    ```"""
    res1 = _clean_and_parse_llm_json(malformed_1)
    assert res1.has_adequate_readme is False
    assert "cinema backend" in res1.summary
    assert len(res1.bullets) == 2

    # 2. Caso con trailing comma
    malformed_2 = """{
      "has_adequate_readme": true,
      "summary": "Clean repo summary.",
      "bullets": ["Bullet 1", "Bullet 2",],
      "technologies": ["Python",],
    }"""
    res2 = _clean_and_parse_llm_json(malformed_2)
    assert res2.has_adequate_readme is True
    assert len(res2.technologies) == 1

