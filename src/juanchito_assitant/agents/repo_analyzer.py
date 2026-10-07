import json
import re

import httpx
from json_repair import loads as repair_loads
from pydantic import BaseModel, Field

from juanchito_assitant.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MODEL_REPO_ANALYZER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
from juanchito_assitant.ingest.github_client import RepoContext

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class RepoAnalysisResult(BaseModel):
    """Resultado estructurado del análisis de un repositorio generado por LLM."""

    has_adequate_readme: bool = Field(
        description="True if the repo already has a comprehensive, informative README.md aligned with actual code. False if missing, trivial stub, or irrelevant."
    )
    summary: str = Field(
        description="Concise 1-2 sentence summary in English of the project purpose, architecture, and value."
    )
    bullets: list[str] = Field(
        description="2 to 4 high-impact resume bullets in English following Google XYZ formula (Accomplished [X] measured by [Y] by doing [Z]). Highlight key technologies and metrics in bold markdown (**tech**, **metric**)."
    )
    technologies: list[str] = Field(
        description="List of detected technologies, libraries, frameworks, and tools (e.g. ['Python', 'FastAPI', 'Playwright', 'Docker', 'OpenCV'])."
    )
    category: str | None = Field(
        default=None,
        description="Concise technical category in 1-3 words in English (e.g. 'AI / Multi-Agent Systems', 'Web Scraping / Backend', 'Cloud / AWS', 'Computer Vision', 'Deep Learning', 'Backend / FastAPI', 'DevOps / Infrastructure', 'Algorithms / Data Structures').",
    )
    suggested_readme: str | None = Field(
        default=None,
        description="Complete professional README.md in English (with title, overview, architecture/features, prerequisites, setup and usage) ONLY if has_adequate_readme is False.",
    )


def _clean_and_parse_llm_json(content: str) -> RepoAnalysisResult:
    """Extrae, repara y valida un JSON devuelto por un LLM hacia RepoAnalysisResult."""
    cleaned = content.strip()

    # 1. Extraer bloques de código markdown si los hay
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        for p in parts[1:]:
            p_clean = p.lstrip()
            if p_clean.startswith("json"):
                p_clean = p_clean[4:].lstrip()
            if "{" in p_clean and "}" in p_clean:
                cleaned = p_clean
                break

    # 2. Intento estándar directo
    try:
        return RepoAnalysisResult.model_validate_json(cleaned)
    except Exception:
        pass

    # 3. Reparación heurística de claves unificadas tipo: "summary: Some text here...",
    pattern = re.compile(r'^(\s*)\"([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*?)\"(,?)\s*$', re.MULTILINE)
    pre_repaired = pattern.sub(r'\1"\2": "\3"\4', cleaned)

    # 4. Reparación profunda con json_repair (comillas sin escapar, trailing commas, control chars)
    try:
        obj = repair_loads(pre_repaired)
        if isinstance(obj, dict):
            # Normalizar claves si alguna contiene prefijo residual
            for k in list(obj.keys()):
                if ":" in k and " " in k:
                    prefix = k.split(":", 1)[0].strip()
                    val = k.split(":", 1)[1].strip()
                    obj[prefix] = val
                    del obj[k]
            return RepoAnalysisResult.model_validate(obj)
    except Exception:
        pass

    # 5. Fallback final estándar
    return RepoAnalysisResult.model_validate_json(pre_repaired)


class RepoAnalyzer:
    """Analizador asíncrono de repositorios de software con soporte para OpenRouter y Google Gemini."""

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

        # Detección inteligente de proveedor
        if provider:
            self.provider = provider.lower()
        elif OPENROUTER_API_KEY:
            self.provider = "openrouter"
        elif GEMINI_API_KEY or client is not None:
            self.provider = "gemini"
        else:
            self.provider = "none"

        # Configuración según proveedor
        if self.provider == "openrouter":
            self.api_key = api_key or OPENROUTER_API_KEY
            self.model = model or MODEL_REPO_ANALYZER or OPENROUTER_MODEL
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

    def _build_prompt(self, ctx: RepoContext) -> str:
        """Construye un prompt enriquecido con el árbol de código y manifiestos para el LLM."""
        manifests_str = ""
        if ctx.manifests:
            for filename, content in ctx.manifests.items():
                manifests_str += f"\n--- MANIFEST: {filename} ---\n{content}\n"
        else:
            manifests_str = "(No dependency or configuration manifests detected)"

        tree_str = "\n".join(ctx.tree_paths[:120]) if ctx.tree_paths else "(Empty file tree)"
        readme_status = (
            f"Filename: {ctx.readme_filename}\nContent:\n{ctx.readme_content}"
            if ctx.readme_content
            else "(No README file found or file is empty)"
        )

        return f"""You are an elite Staff Software Engineer and Technical Recruiter analyzing a GitHub repository to include it in a top-tier software engineering resume (resume.lol style) and evaluate its documentation health.

REPOSITORY INFORMATION:
- Name: {ctx.repo_name}
- Owner: {ctx.owner}
- Target Branch: {ctx.branch}
- GitHub URL: {ctx.html_url}
- GitHub Description: {ctx.description or "None provided"}

FILE TREE (Top files):
{tree_str}

TECHNICAL MANIFESTS DETECTED:
{manifests_str}

CURRENT README STATUS:
{readme_status}

YOUR TASKS:
1. DOCUMENTATION AUDIT (`has_adequate_readme` & `suggested_readme`):
   - Assess whether the current README is complete, accurate, and genuinely describes the real code in the repository.
   - If missing, empty, a trivial one-liner stub (e.g. just "# {ctx.repo_name}"), or completely unrelated to the repository's real content, set `has_adequate_readme = False`.
   - If `has_adequate_readme == False`, author a complete, professional, production-ready `suggested_readme` in Markdown (English) including: Badges, Title, Overview, Architecture/Key Features, Tech Stack, Prerequisites, Installation & Run instructions.
   - If `has_adequate_readme == True`, set `suggested_readme = None`.

2. RESUME IMPACT BULLETS (`bullets`):
   - Generate 2 to 4 impactful technical bullet points in English for a Backend / Software Engineer CV.
   - Follow the Google XYZ formula: "Accomplished [X], as measured by [Y], by doing [Z]".
   - Highlight technologies, tools, and quantified metrics in bold markdown (e.g. "**Python**, **FastAPI**, **Docker**", "**40% latency reduction**").

3. TECHNOLOGIES & SUMMARY:
   - Extract verified technologies, frameworks, and libraries actually used in the project (`technologies`).
   - Write a concise 1-2 sentence summary of the project's engineering value (`summary`).

4. TECHNICAL CATEGORY (`category`):
   - Classify the repository into a concise, professional technical classification (1 to 3 words, e.g. "AI / Multi-Agent Systems", "Web Scraping / Backend", "Cloud / AWS", "Computer Vision", "Deep Learning", "Backend / FastAPI", "DevOps / Infrastructure", "Compilers", "Distributed Systems").
"""

    async def _analyze_openrouter(self, prompt: str) -> RepoAnalysisResult:
        """Envía la solicitud asíncrona a OpenRouter usando httpx."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/MateoPissarello/juanchito-assitant",
            "X-Title": "juanchito-assitant",
            "Content-Type": "application/json",
        }
        schema_json = json.dumps(RepoAnalysisResult.model_json_schema())
        system_prompt = (
            "You are an elite Staff Software Engineer and Technical Recruiter. "
            "Analyze the provided repository and return your analysis strictly as a JSON object matching this schema:\n"
            f"{schema_json}\n"
            'CRITICAL: Every key MUST be enclosed in double quotes followed by a colon and the value, e.g. "summary": "...". NEVER merge key and value like "summary: ...". Return ONLY the valid raw JSON object.'
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.http_transport) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return _clean_and_parse_llm_json(content)

    async def _analyze_gemini(self, prompt: str) -> RepoAnalysisResult:
        """Envía la solicitud asíncrona a Google Gemini usando google-genai."""
        if not self.gemini_client:
            raise ValueError("GEMINI_API_KEY no configurada o cliente de Gemini no disponible.")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RepoAnalysisResult,
            temperature=0.2,
        )

        response = await self.gemini_client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        return _clean_and_parse_llm_json(response.text)

    async def analyze(self, ctx: RepoContext) -> RepoAnalysisResult:
        """Punto de entrada asíncrono para analizar el repositorio con el proveedor activo."""
        prompt = self._build_prompt(ctx)

        if self.provider == "openrouter":
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY no está configurada.")
            return await self._analyze_openrouter(prompt)
        elif self.provider == "gemini":
            if not self.api_key and not self.gemini_client:
                raise ValueError("GEMINI_API_KEY no está configurada.")
            return await self._analyze_gemini(prompt)
        else:
            raise ValueError(
                "No se encontró un proveedor de IA configurado. Por favor define OPENROUTER_API_KEY o GEMINI_API_KEY en tu .env."
            )
