# ==============================================================================
# Stage 1: Frontend Builder (React 19 + Vite + Tailwind CSS v4)
# ==============================================================================
FROM node:22-alpine AS web-builder

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


# ==============================================================================
# Stage 2: Backend Runtime (FastAPI + SQLModel + uv) Serving Frontend SPA
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PORT=8000

WORKDIR /app

# Copiar metadatos de dependencias primero para aprovechar caché de capas Docker
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Instalar paquete y dependencias de producción en .venv
RUN uv sync --frozen --no-dev

# Copiar plantillas base y el bundle estático compilado desde el Stage 1
COPY data/examples/ ./data/examples/
COPY --from=web-builder /app/web/dist ./web/dist

# Asegurar directorios de datos
RUN mkdir -p /app/data/outputs

EXPOSE 8000

# Render inyecta dinámicamente la variable $PORT en tiempo de ejecución
CMD ["sh", "-c", "uv run uvicorn juanchito_assitant.web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
