"""Check offline route behavior without importing optional provider SDKs."""

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_unconfigured_ingestion_fails_closed(monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.post("/v1/videos").status_code == 503


def test_live_evidence_is_disabled_until_operator_controls_exist(monkeypatch):
    monkeypatch.setenv("SEARCH_PROVIDER", "tavily")
    with TestClient(app) as client:
        response = client.post("/v1/evidence/refresh", json={"exercise_id": "lat_pulldown", "technique_question": "form"})
    assert response.status_code == 503


def test_openapi_exposes_result_contract():
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
    assert "AnalysisResult" in schema["components"]["schemas"]
    response = schema["paths"]["/v1/analyses/{analysis_id}/result"]["get"]["responses"]["200"]
    assert response["content"]["application/json"]["schema"]["$ref"].endswith("/AnalysisResult")
