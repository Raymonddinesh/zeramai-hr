"""
test_wf_skills_succession_talent.py - Module 17: Skills Inventory, Critical Roles, Succession & Talent Pools
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS = {
    "SUPER_ADMIN": ("superadmin@zeramai.com", "ChangeMe123!"),
    "HR_ADMIN": ("admin@example.com", "ChangeMe123!"),
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


def test_skills_inventory_and_gap_analysis():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    # 1. Create a Skill with levels
    skill_resp = client.post("/api/v3/workforce-planning/skills", json={
        "code": "SKILL-K8S-DEVOPS",
        "name": "Kubernetes & Multi-Cloud DevOps",
        "category": "TECHNICAL",
        "description": "Cluster management, Helm charts, Service mesh, CI/CD",
        "active": True,
        "levels": [
            {"code": "L1", "name": "Basic Operations", "rank": 1},
            {"code": "L2", "name": "Cluster Management", "rank": 2},
            {"code": "L3", "name": "Production Architecture", "rank": 3},
            {"code": "L4", "name": "Expert / Site Architect", "rank": 4},
        ]
    })
    assert skill_resp.status_code in [200, 201]
    sk = skill_resp.json()
    skill_id = sk["id"]
    assert len(sk["levels"]) == 4

    # 2. Record employee skill
    from app.database import SessionLocal
    from app.models import Person
    db = SessionLocal()
    person = db.query(Person).first()
    person_id = person.id
    db.close()

    emp_sk_resp = client.post("/api/v3/workforce-planning/employee-skills", json={
        "person_id": person_id,
        "skill_id": skill_id,
        "proficiency": 3.0,
        "source": "SELF_REPORTED",
        "effective_from": "2026-01-01",
    })
    assert emp_sk_resp.status_code in [200, 201]
    emp_sk = emp_sk_resp.json()
    emp_sk_id = emp_sk["id"]
    assert emp_sk["verified"] is False

    # 3. Verify employee skill (HR / Admin action)
    verify_resp = client.post(f"/api/v3/workforce-planning/employee-skills/{emp_sk_id}/verify", json={})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True

    # 4. Create Skill Requirement
    req_resp = client.post("/api/v3/workforce-planning/skill-requirements", json={
        "skill_id": skill_id,
        "required_level": 3,
        "required_headcount": 4.0,
        "priority": "CRITICAL",
        "effective_from": "2026-01-01",
    })
    assert req_resp.status_code in [200, 201]

    # 5. Evaluate Skill Gap Analysis
    gap_resp = client.get("/api/v3/workforce-planning/skill-gaps")
    assert gap_resp.status_code == 200
    gaps = gap_resp.json()
    assert len(gaps) >= 1
    k8s_gap = [g for g in gaps if g.get("skill_name") == "Kubernetes & Multi-Cloud DevOps"]
    assert len(k8s_gap) >= 1
    assert k8s_gap[0]["required_headcount"] == 4.0
    assert k8s_gap[0]["available_headcount"] == 1.0
    assert k8s_gap[0]["gap_headcount"] == 3.0


def test_critical_roles_and_succession_planning():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    # Fetch a position
    p_resp = client.get("/api/v3/workforce-planning/positions")
    assert p_resp.status_code == 200
    positions = p_resp.json()
    assert len(positions) >= 1
    pos_id = positions[0]["id"]

    # 1. Designate Critical Role
    cr_resp = client.post("/api/v3/workforce-planning/critical-roles", json={
        "position_id": pos_id,
        "criticality": "CRITICAL",
        "business_impact": "Direct operational impact on core payroll and statutory engine",
        "replacement_difficulty": "EXTREME",
        "vacancy_risk": "HIGH",
        "status": "ACTIVE",
    })
    assert cr_resp.status_code in [200, 201]
    cr_data = cr_resp.json()
    cr_id = cr_data["id"]

    # 2. Create Succession Plan
    from app.database import SessionLocal
    from app.models import Person
    db = SessionLocal()
    persons = db.query(Person).all()
    p_cand_id = persons[0].id
    db.close()

    sp_resp = client.post("/api/v3/workforce-planning/succession-plans", json={
        "critical_role_id": cr_id,
        "target_date": "2026-12-31",
        "candidates": [
            {
                "person_id": p_cand_id,
                "readiness_level": "READY_NOW",
                "development_actions": "Complete executive leadership shadowing and board reporting",
                "target_readiness_date": "2026-06-30",
                "nomination_status": "SHORTLISTED",
            }
        ]
    })
    assert sp_resp.status_code in [200, 201]
    sp_data = sp_resp.json()
    assert sp_data["status"] == "ACTIVE"
    assert len(sp_data["candidates"]) == 1
    assert sp_data["candidates"][0]["readiness_level"] == "READY_NOW"


def test_talent_pool_management():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    from app.database import SessionLocal
    from app.models import Person
    db = SessionLocal()
    persons = db.query(Person).all()
    p_ids = [p.id for p in persons[:2]]
    db.close()

    # 1. Create Talent Pool
    pool_resp = client.post("/api/v3/workforce-planning/talent-pools", json={
        "name": "Next-Gen Engineering Leads",
        "description": "High-potential architects and senior engineering managers",
        "purpose": "LEADERSHIP_PIPELINE",
        "member_person_ids": p_ids,
    })
    assert pool_resp.status_code in [200, 201]
    pool = pool_resp.json()
    pool_id = pool["id"]
    assert pool["member_count"] == len(p_ids)

    # 2. Retrieve Talent Pool with members
    get_pool = client.get(f"/api/v3/workforce-planning/talent-pools/{pool_id}")
    assert get_pool.status_code == 200
    pool_detail = get_pool.json()
    assert len(pool_detail["members"]) == len(p_ids)
    assert pool_detail["members"][0]["person_id"] in p_ids
