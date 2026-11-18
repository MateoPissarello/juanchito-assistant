import asyncio
from dataclasses import dataclass
import json
import logging
import random
from typing import Any
import httpx
import json_repair

logger = logging.getLogger(__name__)


class OpenRouterError(RuntimeError):
    """Excepción para errores al invocar la API de OpenRouter."""

    def __init__(self, message: str, status_code: int | None = None, raw_detail: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.raw_detail = raw_detail


@dataclass
class OpenRouterResponse:
    """Respuesta estructurada de OpenRouter."""

    content: str
    model_used: str
    raw: dict[str, Any]

    def parse_json(self) -> dict[str, Any]:
        """Limpia bloques de código markdown y parsea el contenido a un diccionario JSON."""
        text = self.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        # Extraer substring entre el primer '{' y el último '}' si hay texto circundante
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except Exception:
            # Fallback tolerante con json_repair
            return json_repair.loads(text)


def _normalize_strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Normaliza recursivamente un JSON Schema generado por Pydantic para cumplir con
    Structured Outputs ('strict': True) en OpenRouter/OpenAI:
    - Incluye todas las llaves de 'properties' dentro de 'required' para impedir que
      los decodificadores gramaticales (ej. DeepSeek) omitan campos con valores por defecto
      como 'company_name', 'must_have_skills' o 'experiences'.
    - Establece 'additionalProperties': False en objetos con propiedades definidas.
    """
    normalized = json.loads(json.dumps(schema))

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node["required"] = list(node["properties"].keys())
                if "additionalProperties" not in node:
                    node["additionalProperties"] = False
            for val in node.values():
                _walk(val)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(normalized)
    return normalized


def _extract_error_detail(resp: httpx.Response) -> str:
    """Extrae un mensaje de error legible del cuerpo de respuesta de OpenRouter."""
    try:
        data = resp.json()
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict):
                msg = err.get("message")
                raw = err.get("metadata", {}).get("raw")
                if raw and raw != msg:
                    return f"{msg}: {raw}"
                if msg:
                    return str(msg)
            elif isinstance(err, str):
                return err
            if "message" in data:
                return str(data["message"])
    except Exception:
        pass
    return resp.text.strip() or f"HTTP status {resp.status_code}"


async def call_openrouter(
    api_key: str,
    models: list[str] | str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    response_format: dict[str, Any] | None = None,
    response_schema: Any | None = None,
    max_tokens: int | None = None,
    include_reasoning: bool = False,
    max_retries: int = 3,
    base_delay: float = 2.0,
    timeout: float = 60.0,
    http_transport: httpx.AsyncBaseTransport | None = None,
    extra_headers: dict[str, str] | None = None,
) -> OpenRouterResponse:
    """
    Ejecuta una llamada asíncrona a OpenRouter con:
    1. Lista de modelos fallback nativa ('models': [...]).
    2. Soporte de Structured Outputs ('json_schema') con degradación automática a 'json_object'.
    3. Reintentos exponenciales automáticos para 429 (rate-limit) y 5xx temporales.
    4. Lectura de cabecera 'Retry-After' y jitter aleatorio.
    5. Extracción de mensajes de error limpios y legibles.
    """
    if not api_key:
        raise OpenRouterError("No se proporcionó una OPENROUTER_API_KEY válida.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/MateoPissarello/juanchito-assitant",
        "X-Title": "juanchito-assitant",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    model_chain = [models] if isinstance(models, str) else list(models)
    if not model_chain:
        raise OpenRouterError("La lista de modelos está vacía.")

    payload: dict[str, Any] = {
        "models": model_chain if len(model_chain) > 1 else model_chain[0],
        "messages": messages,
        "temperature": temperature,
    }
    # OpenRouter soporta "models": [...] nativamente para fallback
    if len(model_chain) > 1:
        payload["models"] = model_chain
    else:
        payload["model"] = model_chain[0]

    if response_schema is not None:
        raw_schema = (
            response_schema.model_json_schema()
            if hasattr(response_schema, "model_json_schema")
            else response_schema
        )
        schema_dict = (
            _normalize_strict_json_schema(raw_schema)
            if isinstance(raw_schema, dict)
            else raw_schema
        )
        schema_name = getattr(response_schema, "__name__", "StructuredResponse")
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema_dict,
            },
        }
    elif response_format:
        payload["response_format"] = response_format
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if not include_reasoning:
        payload["include_reasoning"] = False

    last_error_msg = ""
    last_status_code: int | None = None
    schema_downgraded = False

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=http_transport) as client:
                resp = await client.post(url, headers=headers, json=payload)

                # Si un proveedor upstream no soporta json_schema (400/422), degradar transparentemente a json_object
                if (
                    resp.status_code in (400, 422)
                    and not schema_downgraded
                    and isinstance(payload.get("response_format"), dict)
                    and payload["response_format"].get("type") == "json_schema"
                ):
                    schema_downgraded = True
                    payload["response_format"] = {"type": "json_object"}
                    logger.info(
                        "Proveedor en OpenRouter no soportó json_schema estricto (%d); degradando automáticamente a json_object.",
                        resp.status_code,
                    )
                    resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise OpenRouterError("OpenRouter retornó una respuesta sin 'choices'.", status_code=200)

                    msg = choices[0].get("message", {})
                    content = (msg.get("content") or "").strip()
                    if not content and msg.get("reasoning"):
                        content = str(msg["reasoning"]).strip()

                    model_used = data.get("model") or model_chain[0]
                    return OpenRouterResponse(
                        content=content,
                        model_used=model_used,
                        raw=data,
                    )

                last_status_code = resp.status_code
                last_error_msg = _extract_error_detail(resp)

                # Verificar si es un error transitorio reintentable (429 rate limit o 5xx)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    retry_after_hdr = resp.headers.get("Retry-After")
                    wait_time = None
                    if retry_after_hdr:
                        try:
                            wait_time = min(float(retry_after_hdr), 25.0)
                        except ValueError:
                            pass

                    if wait_time is None:
                        # Backoff exponencial con jitter: base * 2^(attempt-1) + [0.2, 1.2]
                        wait_time = base_delay * (2 ** (attempt - 1)) + random.uniform(0.2, 1.2)

                    logger.warning(
                        "OpenRouter respondió %d en intento %d/%d (modelos: %s). Reintentando en %.1fs. Detalle: %s",
                        resp.status_code,
                        attempt,
                        max_retries,
                        model_chain,
                        wait_time,
                        last_error_msg,
                    )
                    await asyncio.sleep(wait_time)
                    continue

                # Error no transitorio o último intento agotado
                raise OpenRouterError(
                    f"Error de OpenRouter ({resp.status_code}): {last_error_msg}",
                    status_code=resp.status_code,
                    raw_detail=last_error_msg,
                )

        except (httpx.TimeoutException, httpx.NetworkError) as net_err:
            last_error_msg = str(net_err)
            if attempt < max_retries:
                wait_time = base_delay * (2 ** (attempt - 1)) + random.uniform(0.2, 1.0)
                logger.warning(
                    "Error de red/timeout con OpenRouter en intento %d/%d: %s. Reintentando en %.1fs...",
                    attempt,
                    max_retries,
                    net_err,
                    wait_time,
                )
                await asyncio.sleep(wait_time)
                continue
            raise OpenRouterError(f"Error de conexión con OpenRouter tras {max_retries} intentos: {net_err}")

    raise OpenRouterError(
        f"Error de OpenRouter ({last_status_code or 'desconocido'}) tras {max_retries} intentos: {last_error_msg}",
        status_code=last_status_code,
        raw_detail=last_error_msg,
    )
