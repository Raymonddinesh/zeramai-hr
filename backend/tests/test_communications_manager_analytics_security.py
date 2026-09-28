"""
test_communications_manager_analytics_security.py - Module 20: Manager Scope, Analytics & RBAC Security Tests
Zeramai Enterprise HRMS
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, User, Person, Engagement

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


def test_manager_team_communication_scope():
    # Login as HR Admin (who has manager/admin scope)
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    resp_team = client.get("/api/v3/communications/team")
    assert resp_team.status_code in [200, 403]
    if resp_team.status_code == 200:
        team_data = resp_team.json()
        assert "team_read_rate_pct" in team_data
        assert "team_acknowledgement_rate_pct" in team_data
        # Ensure individual employee browsing history is NOT in response payload
        assert "employee_browsing_history" not in team_data
        assert "individual_views" not in team_data


def test_communications_and_knowledge_rbac():
    # 1. Unauthenticated requests to knowledge articles or announcements management must return 401
    client.cookies.clear()
    resp_unauth = client.post("/api/v3/knowledge/articles", json={})
    assert resp_unauth.status_code == 401

    resp_unauth2 = client.post("/api/v3/communications/announcements", json={})
    assert resp_unauth2.status_code == 401

    # 2. Regular employee lacks knowledge.manage / communications.manage
    emp_token = login(*CREDENTIALS["EMPLOYEE"])
    set_auth(emp_token)

    resp_emp_cat = client.post("/api/v3/knowledge/categories", json={
        "code": "UNAUTHORIZED-CAT",
        "name": "Unauthorized Category",
    })
    assert resp_emp_cat.status_code == 403

    resp_emp_ann = client.post("/api/v3/communications/announcements", json={
        "title": "Unauthorized Announcement",
        "content_reference": "Should be blocked.",
    })
    assert resp_emp_ann.status_code == 403


def test_cross_tenant_idor_isolation():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Create an article in primary tenant
    cats = client.get("/api/v3/knowledge/categories").json()
    cat_id = cats[0]["id"]
    art = client.post("/api/v3/knowledge/articles", json={
        "category_id": cat_id,
        "title": "Tenant Isolation Test Article",
        "slug": "tenant-iso-test",
        "content_reference": "Isolation details.",
        "article_type": "ARTICLE",
        "visibility": "ALL_EMPLOYEES",
    }).json()

    # Create an announcement
    ann = client.post("/api/v3/communications/announcements", json={
        "title": "Tenant Isolation Test Announcement",
        "content_reference": "Isolation details.",
        "announcement_type": "GENERAL",
    }).json()

    # Simulate cross-tenant query by creating a secondary tenant user
    db = SessionLocal()
    try:
        t2 = db.query(Tenant).filter(Tenant.domain == "seccorp.com").first()
        if not t2:
            t2 = Tenant(name="Secondary Tenant Corp", domain="seccorp.com", is_active=True)
            db.add(t2)
            db.commit()
            db.refresh(t2)
        t2_id = t2.id

        u2 = db.query(User).filter(User.email == "sec_admin@seccorp.com").first()
        if not u2:
            from app.models import UserRole, Person
            from app.auth import hash_password
            p2 = Person(full_name="Secondary Admin", email="sec_admin@seccorp.com")
            db.add(p2)
            db.flush()
            u2 = User(
                email="sec_admin@seccorp.com",
                hashed_password=hash_password("Password123!"),
                role=UserRole.HR_ADMIN,
                person_id=p2.id,
                is_active=True,
            )
            db.add(u2)
            db.commit()
    finally:
        db.close()

    # Login as secondary tenant admin
    sec_token = login("sec_admin@seccorp.com", "Password123!")
    set_auth(sec_token)

    # Attempt to retrieve primary tenant's article -> 404 (IDOR blocked by tenant isolation)
    resp_art_idor = client.get(f"/api/v3/knowledge/articles/{art['id']}", headers={"X-Tenant-ID": t2_id})
    assert resp_art_idor.status_code == 404

    # Attempt to retrieve primary tenant's announcement -> 404 (IDOR blocked by tenant isolation)
    resp_ann_idor = client.get(f"/api/v3/communications/announcements/{ann['id']}", headers={"X-Tenant-ID": t2_id})
    assert resp_ann_idor.status_code == 404


def test_search_analytics_privacy_aggregation():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    resp_analytics = client.get("/api/v3/communications/analytics/search")
    assert resp_analytics.status_code == 200
    analytics_data = resp_analytics.json()
    assert "total_searches" in analytics_data
    assert "zero_result_searches" in analytics_data
    assert "top_search_hashes" in analytics_data

    # Verify query hashes are hashed strings, not plain text queries
    for item in analytics_data["top_search_hashes"]:
        assert "query_hash" in item
        assert len(item["query_hash"]) == 64
