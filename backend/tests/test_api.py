import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["chroma_db_status"] == "connected"

def test_get_settings():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "model_name" in data
    assert "chunk_size" in data
    assert "rerank_top_n" in data

def test_list_documents():
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total_count" in data

def test_prompt_templates():
    response = client.get("/api/evaluate/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 3
    assert any(t["id"] == "tmpl_basic" for t in templates)

