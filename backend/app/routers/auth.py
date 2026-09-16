from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_password
from app.config import settings
from app.database import get_db
from app.deps import get_current_user, log_audit
from app.models import AuditResult, User
from app.schemas import LoginRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if user is None or not verify_password(payload.password, user.hashed_password):
        # Log the failed attempt without revealing whether it was a bad
        # email or bad password (avoid user enumeration).
        log_audit(
            db, user=None, action="login_failed", entity="user",
            entity_id=None, result=AuditResult.FAILURE, request=request,
            metadata={"email_attempted": payload.email},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is inactive")

    token = create_access_token(subject=str(user.id), role=str(user.role.value))
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=60 * 60,
    )

    log_audit(db, user=user, action="login", entity="user", entity_id=user.id,
              result=AuditResult.SUCCESS, request=request)

    return user


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.delete_cookie("access_token")
    log_audit(db, user=current_user, action="logout", entity="user",
              entity_id=current_user.id, result=AuditResult.SUCCESS)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
