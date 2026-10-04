import json
import logging
import re
import httpx

from juanchito_assitant.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MODEL_CV_WRITER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
from juanchito_assitant.models.job import JobRequirements

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)


def _clean_html(html_text: str) -> str:
    """Elimina etiquetas HTML y scripts para obtener texto limpio."""
    text = re.sub(r"<script.*?</script>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class JobAnalyzerAgent:
    """Agente para analizar descripciones de empleo (texto o URL) y extraer requisitos estructurados."""

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
            self.model = model or MODEL_CV_WRITER or OPENROUTER_MODEL
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

    async def fetch_job_text(self, text_or_url: str) -> str:
        """Si la entrada es una URL, descarga el contenido; de lo contrario retorna el texto."""
        text_or_url = text_or_url.strip()
        if text_or_url.startswith("http://") or text_or_url.startswith("https://"):
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.http_transport, follow_redirects=True) as client:
                resp = await client.get(text_or_url, headers=headers)
                resp.raise_for_status()
                return _clean_html(resp.text)
        return text_or_url

    async def analyze_job(self, text_or_url: str) -> JobRequirements:
        """Extrae y estructura los requerimientos de la vacante."""
        raw_text = await self.fetch_job_text(text_or_url)
        if not raw_text.strip():
            raise ValueError("El texto o URL de la vacante no contiene información.")

        prompt = (
            "Analyze the following job description and extract all technical requirements strictly matching the JSON schema:\n"
            "- job_title: Specific professional title (e.g. 'Senior Backend Engineer', 'Cloud Developer').\n"
            "- company_name: Name of hiring company if mentioned, or null.\n"
            "- seniority_level: 'Junior', 'Mid', 'Senior', or 'Lead'.\n"
            "- must_have_skills: Essential technical skills, programming languages, and frameworks explicitly required.\n"
            "- nice_to_have_skills: Desirable or secondary technologies.\n"
            "- core_responsibilities: 3 to 6 key responsibilities.\n"
            "- ats_keywords: High-impact keywords, methodologies (e.g. CI/CD, Agile, Microservices, RAG) for ATS optimization.\n"
            "- role_summary: 2-3 sentence overview in English of the mission and scope of the role.\n\n"
            f"--- JOB DESCRIPTION ---\n{raw_text}\n"
        )

        if self.provider == "openrouter":
            return await self._analyze_openrouter(prompt)
        elif self.provider == "gemini":
            return await self._analyze_gemini(prompt)
        else:
            raise ValueError("No hay proveedor de LLM configurado. Define OPENROUTER_API_KEY o GEMINI_API_KEY.")

    async def _analyze_openrouter(self, prompt: str) -> JobRequirements:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/MateoPissarello/juanchito-assitant",
            "X-Title": "juanchito-assitant",
            "Content-Type": "application/json",
        }
        schema_json = json.dumps(JobRequirements.model_json_schema())
        system_prompt = (
            "You are an expert Technical Recruiter and Job Description Parser. "
            "Extract structured requirements strictly conforming to this JSON schema:\n"
            f"{schema_json}\n"
            "Return ONLY the valid raw JSON object without markdown formatting."
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
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return JobRequirements.model_validate_json(content)

    async def _analyze_gemini(self, prompt: str) -> JobRequirements:
        if not self.gemini_client:
            raise ValueError("GEMINI_API_KEY no configurada o cliente no disponible.")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JobRequirements,
            temperature=0.1,
        )
        resp = await self.gemini_client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return JobRequirements.model_validate_json(resp.text)
