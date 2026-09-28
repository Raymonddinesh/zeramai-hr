"""
test_learning_catalog_courses.py - Module 18: Learning Catalog, Courses, Modules & Paths Tests
Zeramai Enterprise HRMS
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

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


def test_training_provider_and_course_crud():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    # 1. Create Training Provider
    p_resp = client.post("/api/v3/learning/providers", json={
        "name": "Global Tech Academy",
        "provider_type": "EXTERNAL",
        "website": "https://globaltech.example.com",
        "contact_reference": "partner@globaltech.example.com",
        "active": True,
    })
    assert p_resp.status_code == 201
    provider = p_resp.json()
    provider_id = provider["id"]
    assert provider["name"] == "Global Tech Academy"

    # 2. Create Course
    c_resp = client.post("/api/v3/learning/courses", json={
        "course_code": "CRS-PY-ADV-101",
        "title": "Advanced Python & Async Architectures",
        "description": "Deep dive into asyncio, concurrency, and high-throughput microservices.",
        "category": "TECHNICAL",
        "learning_type": "COURSE",
        "difficulty": "ADVANCED",
        "duration_minutes": 180,
        "provider_id": provider_id,
        "delivery_mode": "ONLINE",
        "language": "en",
        "status": "DRAFT",
        "modules": [
            {
                "title": "Module 1: Asyncio Event Loops",
                "sequence": 1,
                "duration_minutes": 60,
                "mandatory": True,
            },
            {
                "title": "Module 2: Multiprocessing & Shared Memory",
                "sequence": 2,
                "duration_minutes": 120,
                "mandatory": True,
            }
        ]
    })
    assert c_resp.status_code == 201
    course = c_resp.json()
    course_id = course["id"]
    assert course["course_code"] == "CRS-PY-ADV-101"
    assert course["module_count"] == 2
    assert course["status"] == "DRAFT"

    # 3. Add Module to Course
    m_resp = client.post(f"/api/v3/learning/courses/{course_id}/modules", json={
        "title": "Module 3: Production Profiling",
        "sequence": 3,
        "duration_minutes": 45,
        "mandatory": False,
    })
    assert m_resp.status_code == 201
    assert m_resp.json()["title"] == "Module 3: Production Profiling"

    # 4. Update Course
    up_resp = client.put(f"/api/v3/learning/courses/{course_id}", json={
        "title": "Advanced Python & High-Scale Microservices"
    })
    assert up_resp.status_code == 200
    assert up_resp.json()["title"] == "Advanced Python & High-Scale Microservices"

    # 5. Course Publishing Lifecycle
    pub_resp = client.post(f"/api/v3/learning/courses/{course_id}/publish")
    assert pub_resp.status_code == 200
    assert pub_resp.json()["status"] == "PUBLISHED"

    # 6. Archive Course
    arch_resp = client.post(f"/api/v3/learning/courses/{course_id}/archive")
    assert arch_resp.status_code == 200
    assert arch_resp.json()["status"] == "ARCHIVED"


def test_learning_paths_and_skill_mapping():
    token = login(*CREDENTIALS["SUPER_ADMIN"])
    set_auth(token)

    # 1. Fetch available skills (from Module 17)
    skills_resp = client.get("/api/v3/workforce-planning/skills")
    assert skills_resp.status_code == 200
    skills = skills_resp.json()
    if not skills:
        sk_resp = client.post("/api/v3/workforce-planning/skills", json={
            "code": "SKILL-FASTAPI",
            "name": "FastAPI Framework",
            "category": "TECHNICAL"
        })
        skill_id = sk_resp.json()["id"]
    else:
        skill_id = skills[0]["id"]

    # 2. Create Course for Path
    c_resp = client.post("/api/v3/learning/courses", json={
        "course_code": "CRS-FASTAPI-BOOT",
        "title": "FastAPI Web Engineering Bootcamp",
        "category": "TECHNICAL",
        "learning_type": "BOOTCAMP",
        "difficulty": "INTERMEDIATE",
        "duration_minutes": 240,
        "delivery_mode": "SELF_PACED",
        "language": "en",
        "status": "PUBLISHED"
    })
    assert c_resp.status_code == 201
    course_id = c_resp.json()["id"]

    # 3. Map Course to Module 17 Skill
    map_resp = client.post(f"/api/v3/learning/courses/{course_id}/skills", json={
        "course_id": course_id,
        "skill_id": skill_id,
        "proficiency_gain": 1.0,
    })
    assert map_resp.status_code == 201
    mapping = map_resp.json()
    assert mapping["skill_id"] == skill_id
    assert mapping["proficiency_gain"] == 1.0

    # 4. Create Learning Path
    lp_resp = client.post("/api/v3/learning/paths", json={
        "name": "Backend Architect Master Track",
        "description": "Comprehensive pathway for backend engineers.",
        "target_role": "Backend Staff Engineer",
        "target_job_family": "Engineering",
        "status": "PUBLISHED",
        "courses": [
            {
                "course_id": course_id,
                "sequence": 1,
                "mandatory": True,
            }
        ]
    })
    assert lp_resp.status_code == 201
    lp = lp_resp.json()
    assert lp["name"] == "Backend Architect Master Track"

    # 5. Get Learning Path Details
    get_lp = client.get(f"/api/v3/learning/paths/{lp['id']}")
    assert get_lp.status_code == 200
    details = get_lp.json()
    assert len(details["path_courses"]) >= 1
    assert details["path_courses"][0]["course_id"] == course_id
