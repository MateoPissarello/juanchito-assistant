import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

COOKIE_NAME = "juanchito_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 días

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = "mateo"
    password: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    auth_enabled: bool
    username: str | None = None


def get_admin_username() -> str:
    return os.getenv("ADMIN_USERNAME", "mateo").strip() or "mateo"


def get_admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "").strip()


def is_auth_enabled() -> bool:
    """El cerrojo de autenticación está activo siempre que ADMIN_PASSWORD esté configurado."""
    return bool(get_admin_password())


def _get_signing_secret() -> bytes:
    explicit_secret = os.getenv("AUTH_SECRET_KEY", "").strip()
    if explicit_secret:
        return explicit_secret.encode("utf-8")
    # Derivar clave determinista del password de administrador si no se definió AUTH_SECRET_KEY
    pwd = get_admin_password() or "juanchito-dev-secret"
    return hashlib.sha256(f"juanchito-hmac:{pwd}".encode("utf-8")).digest()


def create_session_token(username: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    """Genera un token firmado HMAC-SHA256 stateless con fecha de expiración."""
    payload = {
        "u": username,
        "exp": int(time.time()) + ttl_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hmac.new(_get_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_session_token(token: str | None) -> str | None:
    """Verifica la firma HMAC y expiración del token. Retorna el username si es válido."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected_sig = hmac.new(
            _get_signing_secret(),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not secrets.compare_digest(sig, expected_sig):
            return None

        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))

        exp = int(payload.get("exp", 0))
        if exp < int(time.time()):
            return None

        username = str(payload.get("u", ""))
        if not secrets.compare_digest(username, get_admin_username()):
            return None
        return username
    except Exception:
        return None


def get_authenticated_user(request: Request) -> str | None:
    """Extrae y valida la sesión desde la cookie HttpOnly o header Authorization."""
    if not is_auth_enabled():
        return get_admin_username()

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    return verify_session_token(token)


def require_auth(request: Request) -> str:
    """Dependencia FastAPI que protege los endpoints privados cuando ADMIN_PASSWORD está configurado."""
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado. Inicia sesión para acceder a Juanchito Studio.",
        )
    return user


@auth_router.get("/status", response_model=AuthStatusResponse)
def auth_status(request: Request):
    """Retorna el estado actual de la sesión y si la protección por contraseña está activa."""
    enabled = is_auth_enabled()
    user = get_authenticated_user(request)
    return AuthStatusResponse(
        authenticated=user is not None,
        auth_enabled=enabled,
        username=user,
    )


@auth_router.post("/login", response_model=AuthStatusResponse)
def login(payload: LoginRequest, request: Request, response: Response):
    """Valida credenciales del propietario y establece una cookie HttpOnly firmada."""
    if not is_auth_enabled():
        return AuthStatusResponse(
            authenticated=True,
            auth_enabled=False,
            username=get_admin_username(),
        )

    expected_user = get_admin_username()
    expected_pass = get_admin_password()

    user_ok = secrets.compare_digest(payload.username.strip(), expected_user)
    pass_ok = secrets.compare_digest(payload.password, expected_pass)

    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )

    token = create_session_token(expected_user)
    is_https = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "").lower() == "https"
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=is_https,
        path="/",
    )

    return AuthStatusResponse(
        authenticated=True,
        auth_enabled=True,
        username=expected_user,
    )


@auth_router.post("/logout", response_model=AuthStatusResponse)
def logout(response: Response):
    """Cierra la sesión eliminando la cookie HttpOnly."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return AuthStatusResponse(
        authenticated=not is_auth_enabled(),
        auth_enabled=is_auth_enabled(),
        username=None if is_auth_enabled() else get_admin_username(),
    )
