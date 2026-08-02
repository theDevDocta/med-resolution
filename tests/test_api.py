def test_health_endpoint(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database_loaded"] is True
    assert body["drug_count"] == 6
    assert body["alias_count"] > 0


def test_search_endpoint(api_client):
    response = api_client.get("/search", params={"q": "amoxiciline", "limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "amoxiciline"
    assert body["normalized_query"] == "amoxiciline"
    assert any("AMOXICILLINE" in r["canonical_name"] for r in body["results"])
    assert "disclaimer" in body


def test_resolve_endpoint(api_client):
    response = api_client.post(
        "/resolve",
        json={
            "verbatim": "le patient prend de l amoxiciline cinq cents",
            "llm_version": "le patient prend de l'amoxicilline 500 mg",
            "suspected_term": "amoxiciline",
            "context": "infection ORL, trois prises par jour",
            "limit": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["input"]["suspected_term"] == "amoxiciline"
    assert body["candidates"]
    top = body["candidates"][0]
    assert "AMOXICILLINE" in top["canonical_name"]
    assert top["confidence"] in {"high", "medium"}
    assert "disclaimer" in body


def test_resolve_endpoint_requires_verbatim(api_client):
    response = api_client.post("/resolve", json={})
    assert response.status_code == 422


def test_resolve_endpoint_no_reliable_match_notice(api_client):
    response = api_client.post("/resolve", json={"verbatim": "le patient regarde la television ce soir"})
    assert response.status_code == 200
    body = response.json()
    assert body.get("notice")


def test_health_when_database_missing(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.db import connection as connection_module
    from app.main import app

    monkeypatch.setattr(connection_module, "DB_PATH", tmp_path / "missing.sqlite")
    connection_module.reset_connection()
    with TestClient(app) as client:
        response = client.get("/health")
    connection_module.reset_connection()

    assert response.status_code == 200
    body = response.json()
    assert body["database_loaded"] is False
