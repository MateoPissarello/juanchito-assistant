import json
import pytest
import httpx
from juanchito_assitant.agents.llm_client import (
    OpenRouterError,
    OpenRouterResponse,
    call_openrouter,
)


@pytest.mark.anyio
async def test_call_openrouter_success():
    payload_seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal payload_seen
        payload_seen = json.loads(request.read())
        return httpx.Response(
            200,
            json={
                "model": "qwen/qwen-2.5-72b-instruct",
                "choices": [{"message": {"role": "assistant", "content": '{"status": "ok"}'}}],
            },
        )

    transport = httpx.MockTransport(handler)
    res = await call_openrouter(
        api_key="sk-test",
        models=["deepseek/deepseek-chat", "qwen/qwen-2.5-72b-instruct"],
        messages=[{"role": "user", "content": "hi"}],
        http_transport=transport,
    )

    assert res.content == '{"status": "ok"}'
    assert res.model_used == "qwen/qwen-2.5-72b-instruct"
    assert res.parse_json() == {"status": "ok"}
    assert payload_seen["models"] == ["deepseek/deepseek-chat", "qwen/qwen-2.5-72b-instruct"]


@pytest.mark.anyio
async def test_call_openrouter_markdown_json_cleaning():
    def handler(request: httpx.Request) -> httpx.Response:
        markdown_json = "```json\n{\n  \"message\": \"success\"\n}\n```"
        return httpx.Response(
            200,
            json={
                "model": "deepseek/deepseek-chat",
                "choices": [{"message": {"role": "assistant", "content": markdown_json}}],
            },
        )

    transport = httpx.MockTransport(handler)
    res = await call_openrouter(
        api_key="sk-test",
        models="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": "test"}],
        http_transport=transport,
    )

    assert res.parse_json() == {"message": "success"}


@pytest.mark.anyio
async def test_call_openrouter_reasoning_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "typesafe/jev-router",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "reasoning": '{"decision": "APPROVE"}',
                        }
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    res = await call_openrouter(
        api_key="sk-test",
        models=["typesafe/jev-router"],
        messages=[{"role": "user", "content": "test"}],
        http_transport=transport,
    )

    assert res.content == '{"decision": "APPROVE"}'
    assert res.parse_json() == {"decision": "APPROVE"}


@pytest.mark.anyio
async def test_call_openrouter_429_retry_success():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                429,
                json={
                    "error": {
                        "message": "Provider returned error",
                        "metadata": {"raw": "deepseek upstream rate-limit"},
                    }
                },
                headers={"Retry-After": "0.01"},
            )
        return httpx.Response(
            200,
            json={
                "model": "deepseek/deepseek-chat",
                "choices": [{"message": {"role": "assistant", "content": "Resolved after retry"}}],
            },
        )

    transport = httpx.MockTransport(handler)
    res = await call_openrouter(
        api_key="sk-test",
        models=["deepseek/deepseek-chat"],
        messages=[{"role": "user", "content": "test"}],
        base_delay=0.01,
        max_retries=3,
        http_transport=transport,
    )

    assert call_count == 2
    assert res.content == "Resolved after retry"


@pytest.mark.anyio
async def test_call_openrouter_429_exhausted_raises_openrouter_error():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": "Provider returned error",
                    "metadata": {"raw": "upstream rate-limit permanent"},
                }
            },
            headers={"Retry-After": "0.01"},
        )

    transport = httpx.MockTransport(handler)
    with pytest.raises(OpenRouterError) as exc_info:
        await call_openrouter(
            api_key="sk-test",
            models=["deepseek/deepseek-chat"],
            messages=[{"role": "user", "content": "test"}],
            base_delay=0.01,
            max_retries=2,
            http_transport=transport,
        )

    assert call_count == 2
    assert "Provider returned error: upstream rate-limit permanent" in str(exc_info.value)
    assert exc_info.value.status_code == 429


@pytest.mark.anyio
async def test_call_openrouter_structured_output_schema_and_auto_downgrade():
    from pydantic import BaseModel

    class SampleSchema(BaseModel):
        answer: str

    payloads_seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        payloads_seen.append(body)
        # Simular que el primer intento con json_schema es rechazado con 400 por proveedor upstream
        if body.get("response_format", {}).get("type") == "json_schema":
            return httpx.Response(
                400,
                json={"error": {"message": "Provider does not support json_schema response_format"}},
            )
        return httpx.Response(
            200,
            json={
                "model": "deepseek/deepseek-chat",
                "choices": [{"message": {"role": "assistant", "content": '{"answer": "42"}'}}],
            },
        )

    transport = httpx.MockTransport(handler)
    res = await call_openrouter(
        api_key="sk-test",
        models="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": "question"}],
        response_schema=SampleSchema,
        http_transport=transport,
    )

    assert len(payloads_seen) == 2
    assert payloads_seen[0]["response_format"]["type"] == "json_schema"
    assert payloads_seen[0]["response_format"]["json_schema"]["name"] == "SampleSchema"
    assert payloads_seen[1]["response_format"] == {"type": "json_object"}
    assert res.parse_json() == {"answer": "42"}


def test_normalize_strict_json_schema_includes_default_fields_in_required():
    from juanchito_assitant.agents.llm_client import _normalize_strict_json_schema
    from juanchito_assitant.models.job import JobRequirements
    from juanchito_assitant.agents.cv_writer import TailoredResumeContent

    job_schema = _normalize_strict_json_schema(JobRequirements.model_json_schema())
    assert set(job_schema["required"]) == {
        "job_title",
        "company_name",
        "seniority_level",
        "must_have_skills",
        "nice_to_have_skills",
        "core_responsibilities",
        "ats_keywords",
        "role_summary",
    }
    assert job_schema["additionalProperties"] is False

    writer_schema = _normalize_strict_json_schema(TailoredResumeContent.model_json_schema())
    assert set(writer_schema["required"]) == {
        "headline",
        "profile_summary",
        "experiences",
        "projects",
        "prioritized_skills",
    }
    assert writer_schema["additionalProperties"] is False

