import pytest
import httpx

from juanchito_assitant.agents.linkedin_parser import LinkedInParserAgent
from juanchito_assitant.models.linkedin import LinkedInProfileExtract


@pytest.mark.anyio
async def test_linkedin_parser_openrouter_mock():
    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{\n'
                        '  "full_name": "Mateo Pissarello",\n'
                        '  "headline": "Backend Engineer",\n'
                        '  "location": "Bogotá, Colombia",\n'
                        '  "summary": "Specialized in Python and Cloud.",\n'
                        '  "experiences": [\n'
                        '    {\n'
                        '      "company": "Icebergdata",\n'
                        '      "role": "Junior Backend Engineer",\n'
                        '      "location": "Bogotá, Colombia",\n'
                        '      "start_date": "Jan. 2026",\n'
                        '      "end_date": "Mar. 2026",\n'
                        '      "is_current": false,\n'
                        '      "is_technical": true,\n'
                        '      "summary": "Web scraping pipelines",\n'
                        '      "bullets": ["Engineered high-scale web scrapers using **Python**."],\n'
                        '      "technologies": ["Python", "Playwright"]\n'
                        '    }\n'
                        '  ],\n'
                        '  "certifications": [\n'
                        '    {\n'
                        '      "issuer": "Amazon Web Services (AWS)",\n'
                        '      "title": "AWS Certified Cloud Practitioner",\n'
                        '      "issue_date": "Dec. 2024"\n'
                        '    }\n'
                        '  ],\n'
                        '  "education": [\n'
                        '    {\n'
                        '      "institution": "Universidad Sergio Arboleda",\n'
                        '      "degree": "B.Sc. in Computer Science & AI",\n'
                        '      "date_range": "Jul. 2022 - Present"\n'
                        '    }\n'
                        '  ],\n'
                        '  "skills": ["Python", "FastAPI", "Docker"],\n'
                        '  "languages": ["Español (Native)", "Inglés (B2)"]\n'
                        '}'
                    )
                }
            }
        ]
    }

    def custom_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response_data)

    transport = httpx.MockTransport(custom_handler)
    agent = LinkedInParserAgent(
        provider="openrouter",
        api_key="fake-test-key",
        http_transport=transport,
    )

    result = await agent.parse("Fake PDF raw text")
    assert isinstance(result, LinkedInProfileExtract)
    assert result.full_name == "Mateo Pissarello"
    assert len(result.experiences) == 1
    assert result.experiences[0].company == "Icebergdata"
    assert result.experiences[0].is_technical is True
    assert "Python" in result.skills
