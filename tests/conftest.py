from pathlib import Path

import pytest

from app.db import connection as connection_module
from app.importers.build_database import build_and_replace

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def built_db_path(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("bdpm") / "bdpm.sqlite"
    build_and_replace(FIXTURES_DIR, db_path)
    return db_path


@pytest.fixture
def resolver(built_db_path, monkeypatch):
    from app.core.resolver import DrugResolver

    monkeypatch.setattr(connection_module, "DB_PATH", built_db_path)
    connection_module.reset_connection()
    yield DrugResolver()
    connection_module.reset_connection()


@pytest.fixture
def api_client(built_db_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(connection_module, "DB_PATH", built_db_path)
    connection_module.reset_connection()
    with TestClient(app) as client:
        yield client
    connection_module.reset_connection()
