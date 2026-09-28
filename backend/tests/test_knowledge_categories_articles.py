"""
test_knowledge_categories_articles.py - Module 20: Knowledge Categories & Article Versioning Tests
Zeramai Enterprise HRMS
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Tenant, User

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


def test_knowledge_category_crud_and_hierarchy():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Create root category
    resp = client.post("/api/v3/knowledge/categories", json={
        "code": "TEST-LEAVE-CAT",
        "name": "Leave, Attendance & PTO Guidelines",
        "description": "Information on paid time off, medical leave, and attendance policies.",
        "display_order": 1,
        "active": True,
    })
    assert resp.status_code == 201, resp.text
    root_cat = resp.json()
    root_id = root_cat["id"]
    assert root_cat["code"] == "TEST-LEAVE-CAT"

    # 2. Create sub-category referencing root
    resp_sub = client.post("/api/v3/knowledge/categories", json={
        "code": "TEST-PARENTAL-LEAVE",
        "name": "Parental & Maternity Leave",
        "description": "Specific procedures for parental and family leave.",
        "parent_id": root_id,
        "display_order": 2,
        "active": True,
    })
    assert resp_sub.status_code == 201, resp_sub.text
    sub_cat = resp_sub.json()
    assert sub_cat["parent_id"] == root_id

    # 3. List categories as tree
    resp_tree = client.get("/api/v3/knowledge/categories?tree=true")
    assert resp_tree.status_code == 200
    tree = resp_tree.json()
    assert any(c["id"] == root_id for c in tree)

    # 4. Update category
    resp_up = client.put(f"/api/v3/knowledge/categories/{root_id}", json={
        "name": "Leave & PTO Guidelines (Updated)",
    })
    assert resp_up.status_code == 200
    assert resp_up.json()["name"] == "Leave & PTO Guidelines (Updated)"


def test_circular_category_prevention():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # Create category A
    resp_a = client.post("/api/v3/knowledge/categories", json={
        "code": "CAT-A-CYCLE",
        "name": "Category A",
        "display_order": 1,
    })
    assert resp_a.status_code == 201
    cat_a_id = resp_a.json()["id"]

    # Attempt 1: Self-parenting
    resp_self = client.put(f"/api/v3/knowledge/categories/{cat_a_id}", json={
        "parent_id": cat_a_id,
    })
    assert resp_self.status_code == 400
    assert "Circular" in resp_self.json()["detail"]

    # Create category B with parent A
    resp_b = client.post("/api/v3/knowledge/categories", json={
        "code": "CAT-B-CYCLE",
        "name": "Category B",
        "parent_id": cat_a_id,
        "display_order": 2,
    })
    assert resp_b.status_code == 201
    cat_b_id = resp_b.json()["id"]

    # Attempt 2: Set A's parent to B (A -> B -> A cycle)
    resp_cycle = client.put(f"/api/v3/knowledge/categories/{cat_a_id}", json={
        "parent_id": cat_b_id,
    })
    assert resp_cycle.status_code == 400
    assert "Circular" in resp_cycle.json()["detail"]


def test_knowledge_article_lifecycle_and_immutable_versioning():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    # 1. Get a category
    cats = client.get("/api/v3/knowledge/categories").json()
    assert len(cats) > 0
    cat_id = cats[0]["id"]

    # 2. Create Draft Article (should create initial version 1)
    create_payload = {
        "category_id": cat_id,
        "title": "Zeramai Information Security Architecture",
        "slug": "zeramai-infosec-arch",
        "summary": "Core standards for zero-trust security and data encryption.",
        "content_reference": "# Zero Trust Security\nAll services require mutual TLS and RBAC authorization.",
        "article_type": "ARTICLE",
        "visibility": "ALL_EMPLOYEES",
        "change_summary": "Initial draft for security architecture",
    }
    resp = client.post("/api/v3/knowledge/articles", json=create_payload)
    assert resp.status_code == 201, resp.text
    art = resp.json()
    art_id = art["id"]
    assert art["status"] == "DRAFT"
    assert art["current_version"] == 1
    assert len(art["versions"]) == 1
    assert art["versions"][0]["version_number"] == 1
    assert "Zero Trust Security" in art["versions"][0]["content_reference"]

    # 3. Update Article Content (should spawn version 2 while keeping version 1 unchanged)
    update_payload = {
        "title": "Zeramai Information Security Architecture v2",
        "content_reference": "# Zero Trust Security v2\nUpdated with hardware security key requirements.",
        "change_summary": "Added hardware token compliance requirement",
    }
    resp_up = client.put(f"/api/v3/knowledge/articles/{art_id}", json=update_payload)
    assert resp_up.status_code == 200, resp_up.text
    updated_art = resp_up.json()
    assert updated_art["current_version"] == 2
    assert len(updated_art["versions"]) == 2

    # Verify version 1 remained immutable
    v1 = next(v for v in updated_art["versions"] if v["version_number"] == 1)
    v2 = next(v for v in updated_art["versions"] if v["version_number"] == 2)
    assert "All services require mutual TLS" in v1["content_reference"]
    assert "hardware security key" in v2["content_reference"]

    # 4. Workflow: Publish
    resp_pub = client.post(f"/api/v3/knowledge/articles/{art_id}/publish")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == "PUBLISHED"
    assert resp_pub.json()["published_at"] is not None

    # 5. Workflow: Archive
    resp_arch = client.post(f"/api/v3/knowledge/articles/{art_id}/archive")
    assert resp_arch.status_code == 200
    assert resp_arch.json()["status"] == "ARCHIVED"


def test_knowledge_article_relations_anti_self_reference():
    hr_token = login(*CREDENTIALS["HR_ADMIN"])
    set_auth(hr_token)

    cats = client.get("/api/v3/knowledge/categories").json()
    cat_id = cats[0]["id"]

    # Create two articles
    art1 = client.post("/api/v3/knowledge/articles", json={
        "category_id": cat_id,
        "title": "Docker & Container Standards",
        "slug": "docker-standards",
        "content_reference": "Container baseline guidelines.",
        "article_type": "GUIDE",
        "visibility": "ALL_EMPLOYEES",
    }).json()

    art2 = client.post("/api/v3/knowledge/articles", json={
        "category_id": cat_id,
        "title": "Kubernetes Cluster Deployment",
        "slug": "k8s-cluster-deploy",
        "content_reference": "Orchestration setup guidelines.",
        "article_type": "GUIDE",
        "visibility": "ALL_EMPLOYEES",
    }).json()

    # Link art1 -> art2 (PREREQUISITE)
    resp_rel = client.post(f"/api/v3/knowledge/articles/{art1['id']}/related", json={
        "related_article_id": art2["id"],
        "relation_type": "PREREQUISITE",
    })
    assert resp_rel.status_code == 201
    assert resp_rel.json()["related_article_id"] == art2["id"]

    # Anti-self relation check: Link art1 -> art1
    resp_self = client.post(f"/api/v3/knowledge/articles/{art1['id']}/related", json={
        "related_article_id": art1["id"],
        "relation_type": "RELATED",
    })
    assert resp_self.status_code == 400
    assert "Self-referencing" in resp_self.json()["detail"]
