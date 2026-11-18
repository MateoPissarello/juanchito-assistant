import html as html_lib
import json
import logging
import re
import httpx

from juanchito_assitant.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MODELS_JOB_ANALYZER,
    MODEL_CV_WRITER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
from juanchito_assitant.agents.llm_client import _normalize_strict_json_schema, call_openrouter
from juanchito_assitant.models.job import JobRequirements

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)


def _normalize_job_url(url: str) -> str:
    """Normaliza URLs de LinkedIn (ej. collections/search con ?currentJobId=...) a la vista pública de la vacante."""
    url = url.strip()
    if "linkedin.com/jobs/" in url and "/jobs/view/" not in url:
        m = re.search(r"[?&]currentJobId=(\d+)", url)
        if m:
            return f"https://www.linkedin.com/jobs/view/{m.group(1)}/"
    return url


def _extract_html_metadata(html_text: str, source_url: str | None = None) -> dict[str, str]:
    """
    Extrae metadatos estructurados de vacantes antes de eliminar scripts y etiquetas meta:
    - JSON-LD (JobPosting -> hiringOrganization.name, title, description)
    - Selectores de cabecera de LinkedIn (topcard__org-name-link, topcard__flavor, h1)
    - Etiquetas <title> y <meta property="og:title" / name="description">
    - Descripción principal (.show-more-less-html__markup)
    """
    meta: dict[str, str] = {}
    if source_url:
        meta["source_url"] = source_url

    # 1. Extraer bloques JSON-LD (Schema.org JobPosting)
    for ld_raw in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        try:
            ld_data = json.loads(ld_raw.strip())
            candidates = ld_data if isinstance(ld_data, list) else [ld_data]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                org = item.get("hiringOrganization")
                if isinstance(org, dict) and org.get("name") and not meta.get("company_name"):
                    meta["company_name"] = str(org["name"]).strip()
                elif isinstance(org, str) and org.strip() and not meta.get("company_name"):
                    meta["company_name"] = org.strip()
                if item.get("title") and not meta.get("job_title"):
                    meta["job_title"] = str(item["title"]).strip()
                if item.get("description") and not meta.get("ld_description"):
                    desc_clean = re.sub(r"<[^>]+>", " ", html_lib.unescape(str(item["description"])))
                    meta["ld_description"] = re.sub(r"\s+", " ", desc_clean).strip()
        except Exception:
            pass

    # 2. Extraer selectores específicos de LinkedIn y cabeceras HTML
    org_link = re.search(
        r'<a[^>]*class=["\'][^"\']*topcard__org-name-link[^"\']*["\'][^>]*>(.*?)</a>',
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if org_link and not meta.get("company_name"):
        org_text = re.sub(r"<[^>]+>", " ", html_lib.unescape(org_link.group(1))).strip()
        if org_text:
            meta["company_name"] = re.sub(r"\s+", " ", org_text)

    if not meta.get("company_name"):
        flavor = re.search(
            r'<span[^>]*class=["\'][^"\']*topcard__flavor["\'][^>]*>(.*?)</span>',
            html_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if flavor:
            flavor_text = re.sub(r"<[^>]+>", " ", html_lib.unescape(flavor.group(1))).strip()
            if flavor_text:
                meta["company_name"] = re.sub(r"\s+", " ", flavor_text)

    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.DOTALL | re.IGNORECASE)
    if h1_match and not meta.get("job_title"):
        h1_text = re.sub(r"<[^>]+>", " ", html_lib.unescape(h1_match.group(1))).strip()
        if h1_text:
            meta["job_title"] = re.sub(r"\s+", " ", h1_text)

    # 3. Extraer <title> y <meta> (og:title, og:site_name, description)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.DOTALL | re.IGNORECASE)
    if title_match:
        page_title = re.sub(r"\s+", " ", html_lib.unescape(title_match.group(1))).strip()
        if page_title:
            meta["page_title"] = page_title

    for m_tag in re.finditer(r"<meta\s+[^>]+>", html_text, flags=re.IGNORECASE):
        tag_str = m_tag.group(0)
        prop_m = re.search(r'(?:property|name)=["\']([^"\']+)["\']', tag_str, flags=re.IGNORECASE)
        cont_m = re.search(r'content=["\']([^"\']+)["\']', tag_str, flags=re.IGNORECASE)
        if prop_m and cont_m:
            key = prop_m.group(1).lower().strip()
            val = re.sub(r"\s+", " ", html_lib.unescape(cont_m.group(1))).strip()
            if key == "og:title" and val and "page_title" not in meta:
                meta["page_title"] = val
            elif key in ("description", "og:description") and val and "meta_description" not in meta:
                meta["meta_description"] = val
            elif key == "og:site_name" and val and val.lower() not in ("linkedin", "linkedin jobs"):
                meta.setdefault("site_name", val)

    # 4. Inferir nombre de empresa desde page_title o meta_description si aún no se detectó
    title_candidate = meta.get("page_title", "")
    if not meta.get("company_name") and title_candidate:
        patterns = [
            # "Role at Company — Location | LinkedIn Jobs"
            r"\bat\s+([^|—–\-]+?)\s*(?:[—–\-]\s*[^|]+)?\s*\|\s*LinkedIn",
            # "Company hiring Role in Location | LinkedIn"
            r"^(.+?)\s+hiring\s+.+?\s+in\s+.+?(?:\|\s*LinkedIn|$)",
            # "Company contrata Role en Location | LinkedIn"
            r"^(.+?)\s+contrata\s+.+?\s+en\s+.+?(?:\|\s*LinkedIn|$)",
            # "Role en Company | LinkedIn"
            r"\ben\s+([^|—–\-]+?)\s*(?:[—–\-]\s*[^|]+)?\s*\|\s*LinkedIn",
            # "Role at Company | ..."
            r"\bat\s+([^|—–]+?)\s*\|",
        ]
        for pat in patterns:
            pm = re.search(pat, title_candidate, flags=re.IGNORECASE)
            if pm:
                comp = pm.group(1).strip()
                if comp and comp.lower() not in ("linkedin", "linkedin jobs"):
                    meta["company_name"] = comp
                    break

    if not meta.get("company_name") and source_url:
        url_patterns = [
            r"boards\.greenhouse\.io/([^/?#]+)",
            r"job-boards\.greenhouse\.io/([^/?#]+)",
            r"jobs\.lever\.co/([^/?#]+)",
            r"jobs\.ashbyhq\.com/([^/?#]+)",
            r"linkedin\.com/jobs/view/[^/?#]*?-at-([a-zA-Z0-9\-]+)-\d+",
        ]
        for pat in url_patterns:
            um = re.search(pat, source_url, flags=re.IGNORECASE)
            if um:
                slug = um.group(1).replace("-", " ").strip()
                if slug:
                    meta["company_name"] = slug.title() if slug.islower() else slug
                    break

    # 5. Extraer el contenedor principal de descripción en LinkedIn si existe
    desc_div = re.search(
        r'<div[^>]*class=["\'][^"\']*show-more-less-html__markup[^"\']*["\'][^>]*>(.*?)</div>',
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if desc_div:
        desc_text = re.sub(r"<[^>]+>", " ", html_lib.unescape(desc_div.group(1)))
        desc_text = re.sub(r"\s+", " ", desc_text).strip()
        if desc_text:
            meta["job_description_body"] = desc_text

    return meta


def _clean_html(html_text: str, source_url: str | None = None) -> str:
    """Extrae metadatos clave y elimina etiquetas HTML/scripts para obtener texto limpio."""
    meta = _extract_html_metadata(html_text, source_url=source_url)

    text = re.sub(r"<script.*?</script>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    header_lines: list[str] = []
    if meta.get("source_url"):
        header_lines.append(f"SOURCE URL: {meta['source_url']}")
    if meta.get("company_name"):
        header_lines.append(f"DETECTED HIRING COMPANY: {meta['company_name']}")
    if meta.get("job_title"):
        header_lines.append(f"DETECTED JOB TITLE: {meta['job_title']}")
    if meta.get("page_title"):
        header_lines.append(f"PAGE TITLE: {meta['page_title']}")
    if meta.get("meta_description"):
        header_lines.append(f"META DESCRIPTION: {meta['meta_description']}")
    if meta.get("job_description_body"):
        header_lines.append(f"PRIMARY JOB DESCRIPTION: {meta['job_description_body']}")
    elif meta.get("ld_description"):
        header_lines.append(f"PRIMARY JOB DESCRIPTION: {meta['ld_description']}")

    if header_lines:
        header_block = "[EXTRACTED PAGE METADATA]\n" + "\n".join(header_lines) + "\n[/EXTRACTED PAGE METADATA]\n\n"
        return f"{header_block}{text}".strip()

    return text


class JobAnalyzerAgent:
    """Agente para analizar descripciones de empleo (texto o URL) y extraer requisitos estructurados."""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | list[str] | None = None,
        client=None,
        http_transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 60.0,
    ):
        self.http_transport = http_transport
        self.timeout = timeout
        self._last_extracted_meta: dict[str, str] = {}

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
            self.model = model or MODELS_JOB_ANALYZER
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
        self._last_extracted_meta = {}
        text_or_url = text_or_url.strip()
        if text_or_url.startswith("http://") or text_or_url.startswith("https://"):
            target_url = _normalize_job_url(text_or_url)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.http_transport, follow_redirects=True) as client:
                resp = await client.get(target_url, headers=headers)
                resp.raise_for_status()
                final_url = str(resp.url)
                self._last_extracted_meta = _extract_html_metadata(resp.text, source_url=final_url)
                return _clean_html(resp.text, source_url=final_url)
        return text_or_url

    async def analyze_job(self, text_or_url: str) -> JobRequirements:
        """Extrae y estructura los requerimientos de la vacante."""
        raw_text = await self.fetch_job_text(text_or_url)
        if not raw_text.strip():
            raise ValueError("El texto o URL de la vacante no contiene información.")

        prompt = (
            "Analyze the following job description and extract all technical requirements strictly matching the JSON schema:\n"
            "- job_title: Specific professional title (e.g. 'Senior Backend Engineer', 'Cloud Developer').\n"
            "- company_name: Name of hiring company (check DETECTED HIRING COMPANY, PAGE TITLE, or job body; use null ONLY if no company is mentioned anywhere).\n"
            "- seniority_level: 'Junior', 'Mid', 'Senior', or 'Lead'.\n"
            "- must_have_skills: Essential technical skills, programming languages, and frameworks explicitly required (extract atomic tool/tech names and short concepts, e.g. ['AWS', 'CDK', 'Terraform', 'RAG', 'Multi-Agent', 'FastAPI'], avoiding long full-sentence bullets).\n"
            "- nice_to_have_skills: Desirable or secondary technologies (extract atomic tool/tech names, e.g. ['Docker', 'Vector Databases', 'LangChain']).\n"
            "- core_responsibilities: 3 to 6 key responsibilities.\n"
            "- ats_keywords: High-impact keywords, methodologies, and specific tools (e.g. CI/CD, Agile, Microservices, RAG, LLMs) for ATS optimization.\n"
            "- role_summary: 2-3 sentence overview in English of the mission and scope of the role.\n\n"
            f"--- JOB DESCRIPTION ---\n{raw_text}\n"
        )

        if self.provider == "openrouter":
            result = await self._analyze_openrouter(prompt)
        elif self.provider == "gemini":
            result = await self._analyze_gemini(prompt)
        else:
            raise ValueError("No hay proveedor de LLM configurado. Define OPENROUTER_API_KEY o GEMINI_API_KEY.")

        # Fallback determinista para company_name si el LLM lo omitió o devolvió un placeholder genérico
        comp_clean = (result.company_name or "").strip()
        if not comp_clean or comp_clean.lower() in ("null", "none", "unknown", "company", "n/a", "not specified"):
            detected_comp = self._last_extracted_meta.get("company_name")
            if not detected_comp:
                m_hdr = re.search(r"DETECTED HIRING COMPANY:\s*(.+)", raw_text)
                if m_hdr:
                    detected_comp = m_hdr.group(1).strip()
            if not detected_comp and result.role_summary:
                m_sum = re.search(r"\b(?:Join|at)\s+([A-Z][A-Za-z0-9.&\- ]{1,35}?)\s+(?:as\b|to\b|is\b|in\b)", result.role_summary)
                if m_sum:
                    detected_comp = m_sum.group(1).strip()
            if detected_comp:
                result.company_name = detected_comp

        return result

    async def _analyze_openrouter(self, prompt: str) -> JobRequirements:
        schema_json = json.dumps(_normalize_strict_json_schema(JobRequirements.model_json_schema()))
        system_prompt = (
            "You are an expert Technical Recruiter and Job Description Parser. "
            "Extract structured requirements strictly conforming to this JSON schema:\n"
            f"{schema_json}\n"
            "Return ONLY the valid raw JSON object without markdown formatting."
        )

        response = await call_openrouter(
            api_key=self.api_key,
            models=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_schema=JobRequirements,
            timeout=self.timeout,
            http_transport=self.http_transport,
        )
        return JobRequirements.model_validate(response.parse_json())

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
