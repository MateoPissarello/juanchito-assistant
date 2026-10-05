from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from juanchito_assitant.web.api import router as api_router
from juanchito_assitant.db.database import init_db

WEB_DIST_DIR = Path(__file__).resolve().parent.parent.parent.parent / "web" / "dist"


def create_app() -> FastAPI:
    """Fábrica de la aplicación FastAPI para Juanchito Assistant."""
    # Asegurar que la base de datos y sus tablas estén inicializadas
    init_db()

    app = FastAPI(
        title="Juanchito Assistant API & Studio",
        description="Career Workbench & Profile Tailoring Engine for resume.lol",
        version="0.1.0",
    )

    # Configuración de CORS permisiva para desarrollo local (Vite en :5173, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registrar rutas de API
    app.include_router(api_router)

    # Servir archivos estáticos de la UI compilada si existen
    if WEB_DIST_DIR.exists() and (WEB_DIST_DIR / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(WEB_DIST_DIR), html=True), name="static")
    else:
        @app.get("/", response_class=HTMLResponse)
        def index_fallback():
            return """
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>Juanchito Assistant API</title>
                <style>
                    body { font-family: system-ui, sans-serif; background: #09090b; color: #f4f4f5; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                    .card { background: #18181b; border: 1px solid #27272a; padding: 2rem; border-radius: 8px; max-width: 520px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
                    h1 { margin-top: 0; font-size: 1.5rem; color: #14b8a6; }
                    a { color: #38bdf8; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                    code { background: #27272a; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9em; font-family: monospace; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Juanchito Assistant Web API</h1>
                    <p>El backend de FastAPI está corriendo correctamente.</p>
                    <p>La interfaz web frontend se está sirviendo en modo desarrollo o aún no ha sido compilada hacia <code>web/dist</code>.</p>
                    <ul>
                        <li><a href="/docs">Swagger UI (/docs)</a></li>
                        <li><a href="/api/health">Health Check (/api/health)</a></li>
                        <li><a href="/api/profile">Perfil Consolidado (/api/profile)</a></li>
                    </ul>
                </div>
            </body>
            </html>
            """

    return app


app = create_app()
