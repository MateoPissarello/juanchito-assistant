from contextlib import contextmanager
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from juanchito_assitant.config import DB_PATH


def get_engine(db_path: Path = DB_PATH):
    """Crea el engine de SQLAlchemy/SQLModel para SQLite."""
    sqlite_url = f"sqlite:///{db_path}"
    # check_same_thread=False permite uso seguro en hilos y futuras apps FastAPI
    return create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})


def init_db(engine=None, db_path: Path = DB_PATH) -> None:
    """Crea todas las tablas definidas en los modelos si no existen y aplica migraciones ligeras."""
    from sqlalchemy import text
    import juanchito_assitant.models.profile  # noqa: F401

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if engine is None:
        engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)

    # Migración ligera automática para columnas añadidas a tablas existentes
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE personalproject ADD COLUMN last_pushed_at VARCHAR;"))
            conn.commit()
        except Exception:
            pass  # La columna ya existe o la tabla se acaba de crear con ella


@contextmanager
def get_session(engine=None, db_path: Path = DB_PATH):
    """Generador de contexto para sesiones de base de datos."""
    if engine is None:
        engine = get_engine(db_path)
    with Session(engine, expire_on_commit=False) as session:
        yield session
