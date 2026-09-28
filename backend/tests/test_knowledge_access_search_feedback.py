"""
test_knowledge_access_search_feedback.py - Module 20: Knowledge Access Control, Search & Feedback Tests
Zeramai Enterprise HRMS
"""
import pytest
import hashlib
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, User, Person, Engagement
from app.models_communications import KnowledgeSearchEvent

client = TestClient(app)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("hr@zeramai.com", "ChangeMe123!"),
    "EMPLOYEE": ("employee@example.com", "ChangeMe123!"),
}


def login(email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    token = resp.cookies.get("access_token") or resp.json().get("access_token")
    assert token
    return token


def set_auth(token: str):
    client.cookies.set("access_token", token)


@pytest.fixture(scope="module", autouse=True)
def seed_data():
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    from app.seed_rbac import main as run_rbac
    from app.seed import run as run_seed
    run_rbac()
    run_seed()
    yield


def test_knowledge_access_rules_server_side_authorization():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    cats = client.get("/api/v3/knowledge/categories").json()
    cat_id = cats[0]["id"]

    # 1. Create an HR_ONLY restricted article
    hr_art = client.post("/api/v3/knowledge/articles", json={
        "category_id": cat_id,
        "title": "Confidential HR Redundancy & Severance Matrix",
        "slug": "hr-confidential-severance-matrix",
        "summary": "Internal guidance for HR management.",
        "content_reference": "Confidential compensation severance formula.",
        "article_type": "REFERENCE",
        "visibility": "HR_ONLY",
    }).json()

    # Publish it
    client.post(f"/api/v3/knowledge/articles/{hr_art['id']}/publish")

    # 2. As EMPLOYEE: Attempt to access this HR_ONLY article
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    resp_denied = client.get(f"/api/v3/knowledge/articles/{hr_art['id']}")
    assert resp_denied.status_code == 403
    assert "not authorized" in resp_denied.json()["detail"].lower()


def test_knowledge_search_authorization_exclusion_and_hashing():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    cats = client.get("/api/v3/knowledge/categories").json()
    cat_id = cats[0]["id"]

    # Create a unique public article and a unique HR-only article with similar keywords
    keyword = "cryptographic_vault_xyz"
    pub_art = client.post("/api/v3/knowledge/articles", json={
        "category_id": cat_id,
        "title": f"Public Guide to {keyword}",
        "slug": f"pub-guide-{keyword}",
        "content_reference": f"How all employees can use {keyword}.",
        "article_type": "GUIDE",
        "visibility": "ALL_EMPLOYEES",
    }).json()
    client.post(f"/api/v3/knowledge/articles/{pub_art['id']}/publish")

    priv_art = client.post("/api/v3/knowledge/articles", json={
        "category_id": cat_id,
        "title": f"Confidential Admin Keys for {keyword}",
        "slug": f"priv-admin-{keyword}",
        "content_reference": f"Master root secrets for {keyword}.",
        "article_type": "REFERENCE",
        "visibility": "HR_ONLY",
    }).json()
    client.post(f"/api/v3/knowledge/articles/{priv_art['id']}/publish")

    # Now as employee: search for the keyword
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    search_resp = client.get(f"/api/v3/knowledge/search?q={keyword}")
    assert search_resp.status_code == 200
    search_data = search_resp.json()

    # Employee MUST see the public article and MUST NOT see the confidential article
    article_ids = [item["id"] for item in search_data["results"]]
    assert pub_art["id"] in article_ids
    assert priv_art["id"] not in article_ids

    # Verify query hash was logged for privacy
    db = SessionLocal()
    try:
        expected_hash = hashlib.sha256(keyword.encode("utf-8")).hexdigest()
        event = db.query(KnowledgeSearchEvent).filter(
            KnowledgeSearchEvent.query_hash == expected_hash,
        ).first()
        assert event is not None
        assert event.result_count == 1
    finally:
        db.close()


def test_knowledge_feedback_and_helpfulness_summary():
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    # Get a published article
    articles = client.get("/api/v3/knowledge/articles").json()
    assert len(articles) > 0
    art_id = articles[0]["id"]

    # 1. Submit HELPFUL feedback
    resp_fb1 = client.post(f"/api/v3/knowledge/articles/{art_id}/feedback", json={
        "article_id": art_id,
        "feedback_type": "HELPFUL",
        "comment": "Very clear and easy to follow!",
    })
    assert resp_fb1.status_code == 201
    assert resp_fb1.json()["feedback_type"] == "HELPFUL"

    # 2. Get aggregate feedback summary
    resp_sum = client.get(f"/api/v3/knowledge/articles/{art_id}/feedback-summary")
    assert resp_sum.status_code == 200
    summary = resp_sum.json()
    assert summary["article_id"] == art_id
    assert summary["total_feedback"] >= 1
    assert summary["helpful_count"] >= 1
    assert summary["helpfulness_percentage"] > 0


def test_knowledge_review_task_lifecycle():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    articles = client.get("/api/v3/knowledge/articles").json()
    art_id = articles[0]["id"]

    # 1. Schedule review task
    resp_task = client.post("/api/v3/knowledge/reviews", json={
        "article_id": art_id,
        "reviewer_user_id": "usr_hr_admin_001",
        "due_at": "2026-10-15T00:00:00Z",
        "review_notes": "Verify against Q4 compliance changes",
    })
    assert resp_task.status_code == 201
    task_id = resp_task.json()["id"]

    # 2. Reviewer completes task and marks REQUIRES_UPDATE
    resp_comp = client.put(f"/api/v3/knowledge/reviews/{task_id}", json={
        "status": "REQUIRES_UPDATE",
        "review_notes": "Outdated section on dental coverage needs revision",
    })
    assert resp_comp.status_code == 200
    assert resp_comp.json()["status"] == "REQUIRES_UPDATE"

    # Verify article status updated to IN_REVIEW
    art_check = client.get(f"/api/v3/knowledge/articles/{art_id}").json()
    assert art_check["status"] == "IN_REVIEW"
