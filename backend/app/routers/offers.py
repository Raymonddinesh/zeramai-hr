"""Phase 3 – Offer letter management."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v2 import CandidateApplication, ApplicationStage
from app.models_v5 import OfferLetter, OfferStatus

router = APIRouter(prefix="/api/offers", tags=["offers"])


class OfferCreate(BaseModel):
    application_id: str
    offered_designation: str
    offered_department: str
    offered_salary: float
    offered_currency: str = "INR"
    joining_date: Optional[date] = None
    offer_expiry_date: Optional[date] = None
    notes: Optional[str] = None


class OfferOut(BaseModel):
    class Config:
        from_attributes = True
    id: str
    application_id: str
    offered_designation: str
    offered_department: str
    offered_salary: float
    offered_currency: str
    joining_date: Optional[date]
    offer_expiry_date: Optional[date]
    status: OfferStatus


@router.post("", response_model=OfferOut, status_code=201)
def create_offer(
    payload: OfferCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:update")),
):
    app_rec = db.query(CandidateApplication).filter(CandidateApplication.id == payload.application_id).first()
    if not app_rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")

    offer = OfferLetter(
        application_id=payload.application_id,
        offered_designation=payload.offered_designation,
        offered_department=payload.offered_department,
        offered_salary=payload.offered_salary,
        offered_currency=payload.offered_currency,
        joining_date=payload.joining_date,
        offer_expiry_date=payload.offer_expiry_date,
        notes=payload.notes,
    )
    db.add(offer)
    # Move application stage to OFFER_SENT
    app_rec.stage = ApplicationStage.OFFER_SENT
    db.commit()
    db.refresh(offer)
    log_audit(db, user=current_user, action="offer_created", entity="offer",
              entity_id=offer.id, result=AuditResult.SUCCESS, request=request)
    return offer


@router.get("/{application_id}", response_model=list[OfferOut])
def list_offers(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:view")),
):
    return db.query(OfferLetter).filter(OfferLetter.application_id == application_id).all()


@router.patch("/{offer_id}/status")
def update_offer_status(
    offer_id: str,
    new_status: OfferStatus,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("candidates:update")),
):
    offer = db.query(OfferLetter).filter(OfferLetter.id == offer_id).first()
    if not offer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")
    offer.status = new_status

    # If accepted, move application to HIRED
    if new_status == OfferStatus.ACCEPTED:
        app_rec = db.query(CandidateApplication).filter(CandidateApplication.id == offer.application_id).first()
        if app_rec:
            app_rec.stage = ApplicationStage.HIRED

    db.commit()
    return {"id": offer_id, "status": new_status}
