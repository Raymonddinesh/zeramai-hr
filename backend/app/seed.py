"""
Run with: python -m app.seed
Creates one login per role so you can exercise RBAC immediately.
Passwords are dev-only placeholders — change before any shared/staging use.
"""
from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import User, UserRole

DEMO_USERS = [
    ("superadmin@zeramai.com", "ChangeMe123!", UserRole.SUPER_ADMIN),
    ("hr@zeramai.com", "ChangeMe123!", UserRole.HR_ADMIN),
    ("manager@zeramai.com", "ChangeMe123!", UserRole.HIRING_MANAGER),
    ("finance@zeramai.com", "ChangeMe123!", UserRole.FINANCE),
    ("employee@example.com", "ChangeMe123!", UserRole.EMPLOYEE),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    from app.models import Role
    try:
        # Load all roles by name
        roles_by_name = {r.name: r for r in db.query(Role).all()}
        
        for email, password, role_enum in DEMO_USERS:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email, hashed_password=hash_password(password), role=role_enum)
                db.add(user)
                db.flush()
            
            # Map legacy enum role to Role entity (enum names are lowercase strings like 'super_admin' or 'employee' in UserRole)
            role_name_str = role_enum.name # SUPER_ADMIN
            if role_name_str in roles_by_name:
                role_obj = roles_by_name[role_name_str]
                if role_obj not in user.roles:
                    user.roles.append(role_obj)
            
        db.commit()
        print(f"Seeded {len(DEMO_USERS)} demo users (or confirmed they exist).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
