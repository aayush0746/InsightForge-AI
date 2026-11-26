from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def _signup_user(email: str, name: str, password: str = "pass1234"):
    res = client.post("/api/auth/signup", json={"name": name, "email": email, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_cross_tenant_document_chat_research_and_project_isolation():
    alice_h = _signup_user("alice_iso@example.com", "Alice Iso")
    bob_h = _signup_user("bob_iso@example.com", "Bob Iso")

    # Alice uploads a secret document
    secret_txt = b"Project Hyperion secret launch code is TITAN-9988-ALPHA."
    up_a = client.post("/api/documents/upload", files={"file": ("alice_secret.txt", secret_txt)}, headers=alice_h)
    assert up_a.status_code == 200
    alice_doc_id = up_a.json()["document"]["document_id"]

    # Bob must NOT see Alice's document in list, detail, preview, file, or delete
    bob_docs = client.get("/api/documents", headers=bob_h).json()["documents"]
    assert all(d["document_id"] != alice_doc_id for d in bob_docs)
    assert client.get(f"/api/documents/{alice_doc_id}", headers=bob_h).status_code == 404
    assert client.get(f"/api/documents/{alice_doc_id}/preview", headers=bob_h).status_code == 404
    assert client.delete(f"/api/documents/{alice_doc_id}", headers=bob_h).status_code == 404

    # Bob querying /api/chat (targeting Alice's doc_id) must NEVER retrieve TITAN-9988-ALPHA
    bob_chat = client.post(
        "/api/chat",
        json={"question": "What is the Project Hyperion secret launch code?", "document_ids": [alice_doc_id]},
        headers=bob_h
    )
    assert bob_chat.status_code == 200
    assert "TITAN-9988-ALPHA" not in bob_chat.json()["answer"]

    # Bob querying /api/research targeting Alice's doc_id must NEVER leak TITAN-9988-ALPHA
    bob_res = client.post(
        "/api/research",
        json={"question": "What is the Project Hyperion secret launch code?", "document_ids": [alice_doc_id], "max_subtasks": 1},
        headers=bob_h
    )
    assert bob_res.status_code == 200
    report = bob_res.json()["report"]
    assert len(report["citations"]) == 0
    assert "TITAN-9988-ALPHA" not in report["executive_summary"]

    # Bob cannot assign Alice's document to his project
    bob_proj = client.post("/api/projects", json={"name": "Bob Project"}, headers=bob_h).json()
    assign_res = client.post(
        f"/api/projects/{bob_proj['id']}/documents",
        json={"document_id": alice_doc_id},
        headers=bob_h
    )
    assert assign_res.status_code == 404

    # Project with 0 assigned docs must NOT leak Alice's doc or even shared docs
    bob_thread = client.post(
        f"/api/projects/{bob_proj['id']}/threads",
        json={"title": "Empty Project Isolation Test"},
        headers=bob_h
    ).json()
    msg_res = client.post(
        f"/api/projects/{bob_proj['id']}/threads/{bob_thread['id']}/messages",
        json={"message": "What is TITAN-9988-ALPHA?"},
        headers=bob_h
    )
    assert msg_res.status_code == 200
    assert "TITAN-9988-ALPHA" not in msg_res.json()["assistant_message"]["content"]
    assert "No documents are currently assigned" in msg_res.json()["assistant_message"]["content"]


def test_guest_session_isolation_and_cleanup():
    g1_client = TestClient(app)
    g2_client = TestClient(app)
    g1 = {"X-Guest-Session-Id": "guest_alpha_111"}
    g2 = {"X-Guest-Session-Id": "guest_beta_222"}

    up1 = g1_client.post("/api/documents/upload", files={"file": ("g1_note.txt", b"Guest one private token G1-XYZ")}, headers=g1)
    assert up1.status_code == 200
    doc1_id = up1.json()["document"]["document_id"]

    # Guest 2 does not see Guest 1's upload, but sees shared college_rules.pdf
    g2_docs = g2_client.get("/api/documents", headers=g2).json()["documents"]
    assert all(d["document_id"] != doc1_id for d in g2_docs)
    assert any(d["filename"] == "college_rules.pdf" for d in g2_docs)

    # Clear Guest 1 data removes doc1_id without deleting shared college_rules.pdf
    clr = g1_client.delete("/api/documents/guest/clear", headers=g1)
    assert clr.status_code == 200
    assert clr.json()["purged_count"] >= 1

    g1_after = g1_client.get("/api/documents", headers=g1).json()["documents"]
    assert all(d["document_id"] != doc1_id for d in g1_after)
    assert any(d["filename"] == "college_rules.pdf" for d in g1_after)


def test_end_to_end_features_chat_research_compare_eval_and_projects():
    headers = _signup_user("e2e_user@example.com", "E2E Researcher")

    # Upload two policy versions
    v1 = client.post(
        "/api/documents/upload",
        files={"file": ("policy_v1.txt", b"Employees receive 15 days paid leave per year. Notice period is 30 days. Stipend is 20000 INR.")},
        headers=headers
    ).json()["document"]["document_id"]

    v2 = client.post(
        "/api/documents/upload",
        files={"file": ("policy_v2.txt", b"Employees receive 20 days paid leave per year. Notice period is 60 days. Remote stipend is 25000 INR. Penalty for breach is 5000 INR.")},
        headers=headers
    ).json()["document"]["document_id"]

    # 1. Fast Grounded RAG chat + history persistence
    chat_res = client.post(
        "/api/chat",
        json={"question": "What is the notice period and stipend in policy_v2?", "document_ids": [v2]},
        headers=headers
    )
    assert chat_res.status_code == 200
    assert chat_res.json()["is_grounded"] is True
    assert "60" in chat_res.json()["answer"]

    hist_res = client.get("/api/chat/history", headers=headers)
    assert hist_res.status_code == 200
    assert len(hist_res.json()["history"]) >= 2

    # 2. Document Compare (404 on invalid doc, 200 on valid pair)
    assert client.post("/api/documents/compare", json={"doc_id_1": v1, "doc_id_2": "missing_id"}, headers=headers).status_code == 404
    cmp_res = client.post("/api/documents/compare", json={"doc_id_1": v1, "doc_id_2": v2}, headers=headers)
    assert cmp_res.status_code == 200
    cmp_data = cmp_res.json()["data"]
    assert cmp_data["doc_a_name"] == "policy_v1.txt"
    assert cmp_data["doc_b_name"] == "policy_v2.txt"
    assert len(cmp_data["comparison_matrix"]) == 5

    # 3. Multi-Agent Research + Report retrieval + Podcast Briefing
    res_out = client.post(
        "/api/research",
        json={"question": "Compare leave and stipend changes in policy_v2", "document_ids": [v2], "max_subtasks": 2},
        headers=headers
    )
    assert res_out.status_code == 200
    report = res_out.json()["report"]
    rid = report["research_id"]
    assert len(report["agent_steps"]) == 6
    assert client.get(f"/api/research/{rid}", headers=headers).status_code == 200
    assert any(r["research_id"] == rid for r in client.get("/api/research/reports", headers=headers).json())

    pod = client.post(
        "/api/research/podcast-briefing",
        json={"text": report["executive_summary"], "topic": "Policy v2"}
    )
    assert pod.status_code == 200
    assert "Welcome to your InsightForge Executive Briefing" in pod.json()["podcast_script"]

    # 4. Projects assign + thread message + delete thread/project
    proj = client.post("/api/projects", json={"name": "HR Policies"}, headers=headers).json()
    assert client.post(f"/api/projects/{proj['id']}/documents", json={"document_id": v2}, headers=headers).status_code == 200
    th = client.post(f"/api/projects/{proj['id']}/threads", json={"title": "Leave Check"}, headers=headers).json()
    tmsg = client.post(
        f"/api/projects/{proj['id']}/threads/{th['id']}/messages",
        json={"message": "How many days of paid leave?"},
        headers=headers
    )
    assert tmsg.status_code == 200
    assert "20 days" in tmsg.json()["assistant_message"]["content"]
    assert client.delete(f"/api/projects/{proj['id']}/threads/{th['id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/projects/{proj['id']}", headers=headers).status_code == 200

    # 5. Prompt Evaluation scoped history
    ev = client.post(
        "/api/evaluate",
        json={
            "question": "How to build a RAG app?",
            "prompts": {
                "Basic": "{question}",
                "Advanced": "You are an expert architect. Answer: {question}. Rules: - Give actionable steps. - Cite sources only."
            },
            "save_to_history": True
        },
        headers=headers
    )
    assert ev.status_code == 200
    run_id = ev.json()["run_id"]
    assert client.get(f"/api/evaluate/history/{run_id}", headers=headers).status_code == 200


def test_operator_bluf_source_grading_and_numeric_deltas():
    op_client = TestClient(app)
    op_h = {"X-Guest-Session-Id": "guest_operator_audit"}

    d1 = op_client.post(
        "/api/documents/upload",
        files={"file": ("sla_v1.txt", b"Vendor SLA uptime is 99.5% with 60 minutes response time and 500 USD penalty.")},
        headers=op_h
    )
    assert d1.status_code == 200
    d1_id = d1.json()["document"]["document_id"]

    d2 = op_client.post(
        "/api/documents/upload",
        files={"file": ("sla_v2.pdf", b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n4 0 obj\n<< /Length 79 >>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Vendor SLA uptime is 99.99% with 15 minutes response and 2500 USD penalty.) Tj\nET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000241 00000 n \n0000000370 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n440\n%%EOF\n")},
        headers=op_h
    )
    assert d2.status_code == 200
    d2_id = d2.json()["document"]["document_id"]

    try:
        res = op_client.post(
            "/api/research",
            json={"question": "Audit vendor SLA uptime guarantees and penalty thresholds", "document_ids": [d2_id], "max_subtasks": 2},
            headers=op_h
        )
        assert res.status_code == 200
        report = res.json()["report"]
        assert "BLUF Verdict" in report["executive_summary"]
        assert any("Grade " in f for f in report["key_findings"])
        assert any("[TOOL-CHECKED METRICS]" in interp for interp in report["ai_interpretations"])

        cmp_res = op_client.post(
            "/api/documents/compare",
            json={"doc_id_1": d1_id, "doc_id_2": d2_id},
            headers=op_h
        )
        assert cmp_res.status_code == 200
        cmp_data = cmp_res.json()["data"]
        assert len(cmp_data["comparison_matrix"]) == 5
        assert "[TOOL-CHECKED NUMERIC DELTAS]" in cmp_data["executive_summary"]
    finally:
        op_client.delete("/api/documents/guest/clear", headers=op_h)
