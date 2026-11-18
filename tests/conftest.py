import os
import pytest
import juanchito_assitant.config  # noqa: F401 - Carga .env primero para limpiar variables sensibles antes de collection

os.environ.pop("DATABASE_URL", None)
os.environ.pop("ADMIN_PASSWORD", None)


@pytest.fixture(autouse=True)
def _isolate_env_from_production_cloud(monkeypatch):
    """Garantiza que la suite de pruebas nunca se conecte por accidente al DATABASE_URL real del .env."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
