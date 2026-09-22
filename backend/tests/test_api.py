import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY set nahi hai"
)


@pytest.fixture
def client(all_guide_answers, theme_items, monkeypatch):
    """conftest.py ke already-computed guide_answers/themes reuse karta hai,
    taaki FastAPI startup dobara LLM calls na kare (token budget bachane ke liye)."""
    import app.main as main_module

    monkeypatch.setattr(main_module, "get_all_guide_answers", lambda *a, **kw: all_guide_answers)
    monkeypatch.setattr(main_module, "get_themes_and_disagreements", lambda *a, **kw: theme_items)

    with TestClient(main_module.app) as c:  # startup event chalega, par patched functions se, LLM call nahi
        yield c


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["experts_loaded"] == 3


def test_experts(client):
    response = client.get("/api/experts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert {e["expert_id"] for e in data} == {"E1", "E2", "E3"}


def test_guide(client):
    response = client.get("/api/guide")
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 6


def test_guide_answers(client):
    response = client.get("/api/guide-answers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 18  # 3 experts x 6 questions
    for item in data:
        if item["status"] == "answered":
            assert all(ev["verified"] for ev in item["evidence"])


def test_themes(client):
    response = client.get("/api/themes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    for item in data:
        assert all(ev["verified"] for ev in item["evidence"])


def test_transcript_by_id(client):
    response = client.get("/api/transcript/E1")
    assert response.status_code == 200
    assert response.json()["name"] == "Dr. Jean Martin"


def test_transcript_not_found(client):
    response = client.get("/api/transcript/E99")
    assert response.status_code == 404


def test_ask(client, monkeypatch):
    """Ye ek endpoint ke through jaata hai isliye ek live LLM call lagti hai,
    par sirf ek — /api/ask deliberately live hai (Q&A free-form hota hai)."""
    response = client.post("/api/ask", json={"question": "What barriers did experts mention?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"answered", "unanswerable"}