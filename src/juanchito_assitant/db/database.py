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
    """Crea todas las tablas definidas en los modelos si no existen."""
    # Asegura que todos los modelos estén importados y registrados en SQLModel.metadata
    import juanchito_assitant.models.profile  # noqa: F401

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if engine is None:
        engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session(engine=None, db_path: Path = DB_PATH):
    """Generador de contexto para sesiones de base de datos."""
    if engine is None:
        engine = get_engine(db_path)
    with Session(engine, expire_on_commit=False) as session:
        yield session
