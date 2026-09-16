from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Define roles and permissions as per PRD
ROLES = [
    "SUPER_ADMIN",
    "HR_ADMIN",
    "HIRING_MANAGER",
    "FINANCE",
    "EMPLOYEE",
]

PERMISSIONS = [
    # Dashboard
    "dashboard:view",
    # Candidates
    "candidates:view",
    "candidates:create",
    "candidates:update",
    "candidates:select",
    "candidates:convert_to_trainee",
    # Employees
    "employees:view",
    "employees:view_own",
    "employees:create",
    "employees:update",
    "employees:delete",
    # Trainees
    "trainees:view",
    "trainees:create",
    "trainees:update",
    # Documents
    "documents:view",
    "documents:view_own",
    "documents:upload",
    "documents:upload_own",
    "documents:update",
    "documents:verify",
    "documents:download",
    "documents:download_own",
    "documents:delete",
    # Evaluations
    "evaluations:view",
    "evaluations:view_own",
    "evaluations:create",
    "evaluations:update",
    "evaluations:submit",
    # Stipends
    "stipends:view",
    "stipends:view_own",
    "stipends:create",
    "stipends:update",
    "stipends:approve",
    # Attendance
    "attendance:view",
    "attendance:view_own",
    "attendance:create",
    "attendance:create_own",
    "attendance:update",
    # Leave
    "leave:view",
    "leave:view_own",
    "leave:create",
    "leave:create_own",
    "leave:approve",
    # Templates
    "templates:view",
    "templates:create",
    "templates:update",
    "templates:delete",
    # Reports
    "reports:view",
    "reports:export",
    # Users & Roles
    "users:view",
    "users:create",
    "users:update",
    "users:delete",
    "roles:view",
    "roles:update",
    # Audit
    "audit:view",
]

ROLE_PERMISSIONS = {
    "SUPER_ADMIN": PERMISSIONS,
    "HR_ADMIN": [
        "dashboard:view",
        "candidates:view",
        "candidates:create",
        "candidates:update",
        "candidates:select",
        "candidates:convert_to_trainee",
        "employees:view",
        "employees:view_own",
        "employees:create",
        "employees:update",
        "employees:delete",
        "trainees:view",
        "trainees:create",
        "trainees:update",
        "documents:view",
        "documents:view_own",
        "documents:upload",
        "documents:upload_own",
        "documents:update",
        "documents:verify",
        "documents:download",
        "documents:download_own",
        "documents:delete",
        "templates:view",
        "templates:create",
        "templates:update",
        "templates:delete",
        "reports:view",
        "reports:export",
        "audit:view",
        "attendance:view",
        "attendance:create",
        "attendance:update",
        "leave:view",
        "leave:create",
        "leave:approve",
        "evaluations:view",
        "evaluations:create",
        "evaluations:update",
        "evaluations:submit",
        "stipends:view",
        "stipends:create",
        "stipends:approve",
    ],
    "HIRING_MANAGER": [
        "dashboard:view",
        "candidates:view",
        "candidates:create",
        "candidates:update",
        "candidates:select",
        "candidates:convert_to_trainee",
        "trainees:view",
        "trainees:create",
        "trainees:update",
        "evaluations:view",
        "evaluations:view_own",
        "evaluations:create",
        "evaluations:update",
        "evaluations:submit",
    ],
    "FINANCE": [
        "dashboard:view",
        "stipends:view",
        "stipends:view_own",
        "stipends:create",
        "stipends:update",
        "stipends:approve",
    ],
    "EMPLOYEE": [
        "dashboard:view",
        "documents:view_own",
        "documents:download_own",
        "documents:upload_own",
        "attendance:view_own",
        "attendance:create_own",
        "leave:view_own",
        "leave:create_own",
        "employees:view_own",
    ],
}

def main():
    import uuid
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Insert roles with generated UUIDs if not existing
    for role_name in ROLES:
        role_id = str(uuid.uuid4())
        session.execute(
            text(
                "INSERT INTO roles (id, name) VALUES (:id, :name) ON CONFLICT (name) DO NOTHING"
            ),
            {"id": role_id, "name": role_name},
        )

    # Insert permissions with generated UUIDs if not existing
    for perm_code in PERMISSIONS:
        perm_id = str(uuid.uuid4())
        session.execute(
            text(
                "INSERT INTO permissions (id, code) VALUES (:id, :code) ON CONFLICT (code) DO NOTHING"
            ),
            {"id": perm_id, "code": perm_code},
        )

    # Build lookup maps for ids
    role_id_map = {row[1]: row[0] for row in session.execute(text("SELECT id, name FROM roles"))}
    perm_id_map = {row[1]: row[0] for row in session.execute(text("SELECT id, code FROM permissions"))}

    # Insert role_permission associations
    for role, perms in ROLE_PERMISSIONS.items():
        role_id = role_id_map.get(role)
        if not role_id:
            continue
        for perm in perms:
            perm_id = perm_id_map.get(perm)
            if not perm_id:
                continue
            session.execute(
                text(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p) ON CONFLICT (role_id, permission_id) DO NOTHING"
                ),
                {"r": role_id, "p": perm_id},
            )

    session.commit()
    print("RBAC seed completed successfully.")

if __name__ == "__main__":
    main()
