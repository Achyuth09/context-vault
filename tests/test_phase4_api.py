"""Phase 4 API smoke tests (in-process; needs Chroma index for rich stats)."""

from fastapi.testclient import TestClient

from context_vault.api import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stats_shape():
    r = client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert "chunks" in body
    assert "by_status" in body
    assert "conflicts_real" in body


def test_chunks_and_conflicts():
    assert client.get("/api/chunks").status_code == 200
    assert client.get("/api/conflicts").status_code == 200


def test_mark_stale_rejects_bad_id():
    r = client.post("/api/docs/-bad/stale")
    assert r.status_code == 400


def test_mark_stale_unknown_doc(monkeypatch):
    def fake(doc_id: str) -> dict:
        return {"doc_id": doc_id, "chunks_updated": 0, "status": "stale"}

    monkeypatch.setattr("context_vault.api.mark_stale", fake)
    r = client.post("/api/docs/no_such_doc/stale")
    assert r.status_code == 404


def test_mark_stale_ok(monkeypatch):
    seen: list[str] = []

    def fake(doc_id: str) -> dict:
        seen.append(doc_id)
        return {"doc_id": doc_id, "chunks_updated": 2, "status": "stale"}

    monkeypatch.setattr("context_vault.api.mark_stale", fake)
    r = client.post("/api/docs/api_version_jan/stale")
    assert r.status_code == 200
    body = r.json()
    assert body["chunks_updated"] == 2
    assert body["status"] == "stale"
    assert seen == ["api_version_jan"]
