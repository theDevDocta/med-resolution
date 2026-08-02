from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import admin as admin_module
from app.core import config
from app.db import connection as connection_module

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    from app.main import app

    db_path = tmp_path / "bdpm.sqlite"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "RAW_DIR", FIXTURES_DIR)
    monkeypatch.setattr(connection_module, "DB_PATH", db_path)
    connection_module.reset_connection()
    with TestClient(app) as client:
        yield client
    connection_module.reset_connection()


def test_update_database_skip_download_builds_from_raw_dir(admin_client):
    response = admin_client.post("/admin/update-database", params={"skip_download": "true"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["drug_count"] == 6
    assert body["alias_count"] > 0

    health = admin_client.get("/health")
    assert health.json()["drug_count"] == 6


def test_update_database_rejects_missing_files(admin_client, monkeypatch, tmp_path):
    empty_raw = tmp_path / "empty_raw"
    empty_raw.mkdir()
    monkeypatch.setattr(config, "RAW_DIR", empty_raw)

    response = admin_client.post("/admin/update-database", params={"skip_download": "true"})
    assert response.status_code == 422


def test_update_database_returns_409_when_already_running(admin_client):
    assert admin_module._update_lock.acquire(blocking=False)
    try:
        response = admin_client.post("/admin/update-database", params={"skip_download": "true"})
        assert response.status_code == 409
    finally:
        admin_module._update_lock.release()


def test_update_database_download_failure_returns_502(admin_client, monkeypatch):
    def fail_download():
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(admin_module, "download_bdpm_files", fail_download)

    response = admin_client.post("/admin/update-database")
    assert response.status_code == 502


def test_update_database_requires_admin_key_when_configured(admin_client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_API_KEY", "secret-key")

    response = admin_client.post("/admin/update-database", params={"skip_download": "true"})
    assert response.status_code == 401

    response = admin_client.post(
        "/admin/update-database",
        params={"skip_download": "true"},
        headers={"X-Admin-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_update_database_accepts_correct_admin_key(admin_client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_API_KEY", "secret-key")

    response = admin_client.post(
        "/admin/update-database",
        params={"skip_download": "true"},
        headers={"X-Admin-Key": "secret-key"},
    )
    assert response.status_code == 200


def test_update_database_requires_api_key_when_configured(admin_client, monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "service-key")

    response = admin_client.post("/admin/update-database", params={"skip_download": "true"})
    assert response.status_code == 401

    response = admin_client.post(
        "/admin/update-database",
        params={"skip_download": "true"},
        headers={"X-API-Key": "service-key"},
    )
    assert response.status_code == 200
