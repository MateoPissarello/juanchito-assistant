from contextlib import contextmanager
import os
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from juanchito_assitant.config import DB_PATH

_ENGINE_CACHE: dict[str, Engine] = {}


def normalize_database_url(raw_url: str) -> str:
    """Normaliza URLs de PostgreSQL (Render, Neon, Supabase) al driver psycopg v3 de SQLAlchemy."""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def resolve_database_url(db_path: Path = DB_PATH, database_url: str | None = None) -> str:
    """Determina la URL efectiva de base de datos (PostgreSQL remoto o SQLite local)."""
    # Si se pasa explícitamente un database_url, usarlo con prioridad
    if database_url is not None and database_url.strip():
        return normalize_database_url(database_url)

    # Si se especificó un db_path distinto al DB_PATH global (ej. en tests unitarios con tmp_path),
    # respetar siempre ese archivo SQLite aislado.
    if db_path != DB_PATH:
        return f"sqlite:///{db_path}"

    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return normalize_database_url(env_url)

    return f"sqlite:///{db_path}"


def get_engine(db_path: Path = DB_PATH, database_url: str | None = None) -> Engine:
    """Crea o reutiliza el engine de SQLAlchemy/SQLModel para SQLite o PostgreSQL."""
    resolved_url = resolve_database_url(db_path=db_path, database_url=database_url)
    if resolved_url in _ENGINE_CACHE:
        return _ENGINE_CACHE[resolved_url]

    kwargs: dict[str, Any] = {"echo": False}
    if resolved_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Pool resiliente para Postgres serverless (Neon / Supabase / Render)
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 300

    engine = create_engine(resolved_url, **kwargs)
    _ENGINE_CACHE[resolved_url] = engine
    return engine


def init_db(engine: Engine | None = None, db_path: Path = DB_PATH) -> None:
    """Crea todas las tablas definidas en los modelos si no existen y aplica migraciones ligeras."""
    from sqlalchemy import text
    import juanchito_assitant.models.profile  # noqa: F401

    if engine is None:
        resolved_url = resolve_database_url(db_path=db_path)
        if resolved_url.startswith("sqlite"):
            db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = get_engine(db_path=db_path)

    SQLModel.metadata.create_all(engine)

    # Migración ligera automática para columnas añadidas a tablas SQLite existentes
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE personalproject ADD COLUMN last_pushed_at VARCHAR;"))
                conn.commit()
            except Exception:
                pass  # La columna ya existe o la tabla se acaba de crear con ella


@contextmanager
def get_session(engine: Engine | None = None, db_path: Path = DB_PATH):
    """Generador de contexto para sesiones de base de datos."""
    if engine is None:
        engine = get_engine(db_path=db_path)
    with Session(engine, expire_on_commit=False) as session:
        yield session
