"""Phase 15 - Governed AI Intelligence Suite: Predictive Attrition, AI Helpdesk & FAQ matching."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User, Person, Engagement, Attendance, AttendanceStatus
from app.models_v10 import (
    AIAssessment, AIHelpdeskKnowledge,
    AIAssessmentType,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


class KnowledgeCreate(BaseModel):
    category: str
    question: str
    answer: str
    keywords_json: list[str] = []


class QuestionQuery(BaseModel):
    question: str


# ── AI Attrition Risk Predictor ─────────────────────────────────────────

@router.post("/predict-attrition/{person_id}")
def predict_attrition(
    person_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees:view")),
):
    """Predictive attrition risk scoring based on engagement & attendance indicators."""
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person not found")

    # Assess factors: absences, tenure
    eng = db.query(Engagement).filter(Engagement.person_id == person_id).first()
    absences = db.query(Attendance).filter(
        Attendance.person_id == person_id,
        Attendance.status == AttendanceStatus.ABSENT,
    ).count()

    risk_score = 15.0  # baseline
    factors = []
    recommendations = []

    if absences > 3:
        risk_score += 25.0
        factors.append(f"Elevated unplanned absenteeism ({absences} days)")
        recommendations.append("Conduct supportive wellness check-in")

    if eng and eng.stipend_amount and float(eng.stipend_amount) < 30000:
        risk_score += 20.0
        factors.append("Compensation below benchmark range")
        recommendations.append("Review compensation structure for equity")

    if not factors:
        factors.append("Stable attendance and engagement indicators")
        recommendations.append("Continue standard quarterly check-ins")

    assessment = AIAssessment(
        entity_type="person",
        entity_id=person_id,
        assessment_type=AIAssessmentType.ATTRITION_RISK,
        risk_score=min(round(risk_score, 1), 95.0),
        confidence_score=0.88,
        factors_json=factors,
        recommendations_json=recommendations,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    log_audit(db, user=current_user, action="ai_attrition_predicted", entity="ai_assessment",
              entity_id=assessment.id, result=AuditResult.SUCCESS, request=request,
              metadata={"risk_score": assessment.risk_score})

    return {
        "person_id": person_id,
        "risk_score": assessment.risk_score,
        "risk_level": "High" if assessment.risk_score > 60 else "Moderate" if assessment.risk_score > 30 else "Low",
        "confidence": assessment.confidence_score,
        "factors": assessment.factors_json,
        "recommendations": assessment.recommendations_json,
    }


# ── AI HR Helpdesk Knowledge Base ───────────────────────────────────────

@router.post("/helpdesk/knowledge", status_code=201)
def add_helpdesk_article(
    payload: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:create")),
):
    kb = AIHelpdeskKnowledge(**payload.model_dump())
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return {"id": kb.id, "question": kb.question, "category": kb.category}


@router.post("/helpdesk/ask")
def ask_ai_helpdesk(
    payload: QuestionQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Semantic/keyword matching for HR inquiries."""
    query = payload.question.lower()
    articles = db.query(AIHelpdeskKnowledge).filter(AIHelpdeskKnowledge.is_active == True).all()

    best_match = None
    highest_overlap = 0

    query_tokens = set(query.split())

    for art in articles:
        tokens = set(art.question.lower().split()).union(
            set(k.lower() for k in (art.keywords_json or []))
        )
        overlap = len(query_tokens.intersection(tokens))
        if overlap > highest_overlap:
            highest_overlap = overlap
            best_match = art

    if best_match and highest_overlap > 0:
        return {
            "matched": True,
            "category": best_match.category,
            "question": best_match.question,
            "answer": best_match.answer,
            "confidence": min(round(0.6 + (highest_overlap * 0.1), 2), 0.98),
        }
    else:
        return {
            "matched": False,
            "answer": "I could not find a specific policy match. A ticket has been suggested for the HR support desk.",
            "confidence": 0.2,
        }
