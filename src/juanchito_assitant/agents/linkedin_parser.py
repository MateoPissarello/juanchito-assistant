import json
import logging
import httpx

from juanchito_assitant.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MODEL_LINKEDIN_PARSER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
from juanchito_assitant.models.linkedin import LinkedInProfileExtract

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)


class LinkedInParserAgent:
    """Agente LLM para interpretar texto crudo extraído de exportaciones oficiales de LinkedIn en PDF."""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        client=None,
        http_transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 60.0,
    ):
        self.http_transport = http_transport
        self.timeout = timeout

        if provider:
            self.provider = provider.lower()
        elif OPENROUTER_API_KEY:
            self.provider = "openrouter"
        elif GEMINI_API_KEY or client is not None:
            self.provider = "gemini"
        else:
            self.provider = "none"

        if self.provider == "openrouter":
            self.api_key = api_key or OPENROUTER_API_KEY
            self.model = model or MODEL_LINKEDIN_PARSER or OPENROUTER_MODEL
            self.gemini_client = None
        elif self.provider == "gemini":
            self.api_key = api_key or GEMINI_API_KEY
            self.model = model or GEMINI_MODEL
            if client:
                self.gemini_client = client
            elif self.api_key and genai:
                self.gemini_client = genai.Client(api_key=self.api_key)
            else:
                self.gemini_client = None
        else:
            self.api_key = api_key or ""
            self.model = model or ""
            self.gemini_client = None

    def _build_prompt(self, raw_text: str) -> str:
        return (
            "Below is raw extracted text from an official LinkedIn profile PDF export. "
            "Because LinkedIn uses a two-column layout, text from the sidebar (Contact, Top Skills, Certifications, Languages) "
            "may be interleaved with main body content (Headline, About/Extracto, Experience, Education). "
            "The content may be in English, Spanish, or both.\n\n"
            "Please carefully parse, disambiguate, and structure the data according to the schema:\n"
            "- Normalize company names (e.g., 'Blend' or 'Blend360', 'Icebergdata', 'PhenoScience').\n"
            "- Normalize job titles and locations.\n"
            "- Normalize dates into 'Month. Year' (e.g. 'Jan. 2026', 'Nov. 2024') or 'Present'.\n"
            "- Set `is_technical=True` for software, backend, data, AI, and cloud roles. Set `is_technical=False` for customer support, call center, sales, non-technical jobs.\n"
            "- Structure bullet points into clear, high-impact resume bullets in English (translating if needed) with key metrics and technologies in bold markdown (**tech**, **metrics**).\n"
            "- Extract technologies, tools, and frameworks for each experience.\n"
            "- Extract all certifications with issuer and title.\n"
            "- Extract all education degrees, dates, and institutions.\n"
            "- Extract technical skills and language proficiencies.\n\n"
            f"--- RAW LINKEDIN PDF TEXT ---\n{raw_text}\n"
        )

    async def parse(self, raw_text: str) -> LinkedInProfileExtract:
        """Parsea el texto del PDF de LinkedIn devolviendo un LinkedInProfileExtract estructurado."""
        if not raw_text.strip():
            raise ValueError("El texto crudo del PDF está vacío.")

        prompt = self._build_prompt(raw_text)

        if self.provider == "openrouter":
            return await self._parse_openrouter(prompt)
        elif self.provider == "gemini":
            return await self._parse_gemini(prompt)
        else:
            raise ValueError(
                "No hay proveedor de LLM configurado. Define OPENROUTER_API_KEY o GEMINI_API_KEY."
            )

    async def _parse_openrouter(self, prompt: str) -> LinkedInProfileExtract:
        """Envía la solicitud asíncrona a OpenRouter con esquema JSON estructurado."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/MateoPissarello/juanchito-assitant",
            "X-Title": "juanchito-assitant",
            "Content-Type": "application/json",
        }
        schema_json = json.dumps(LinkedInProfileExtract.model_json_schema())
        system_prompt = (
            "You are an elite Senior Technical Recruiter and Career Architecture AI specialized in parsing LinkedIn profile exports. "
            "You must parse the raw profile text and return strictly a valid JSON object conforming to this JSON schema:\n"
            f"{schema_json}\n"
            "Return ONLY the valid raw JSON object. Do not include markdown code block markers or conversational preamble."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.http_transport) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return LinkedInProfileExtract.model_validate_json(content)

    async def _parse_gemini(self, prompt: str) -> LinkedInProfileExtract:
        """Envía la solicitud asíncrona a Google Gemini usando google-genai."""
        if not self.gemini_client:
            raise ValueError("GEMINI_API_KEY no configurada o cliente de Gemini no disponible.")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LinkedInProfileExtract,
            temperature=0.1,
        )

        response = await self.gemini_client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return LinkedInProfileExtract.model_validate_json(response.text)
