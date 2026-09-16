"""Phase 13 - Multi-Country Localization: Calendars, Holidays, Currency FX."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.deps import get_current_user, require_permission, log_audit
from app.models import AuditResult, User
from app.models_v10 import (
    HolidayCalendar, Holiday, CurrencyRate,
    HolidayType,
)

router = APIRouter(prefix="/api/localization", tags=["localization"])


class CalendarCreate(BaseModel):
    name: str
    country_code: str
    year: int


class CalendarOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    name: str
    country_code: str
    year: int
    is_active: bool


class HolidayCreate(BaseModel):
    name: str
    date: date
    holiday_type: HolidayType = HolidayType.PUBLIC
    is_mandatory: bool = True


class HolidayOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    name: str
    date: date
    holiday_type: HolidayType
    is_mandatory: bool


class CurrencyRateUpsert(BaseModel):
    from_currency: str
    to_currency: str
    exchange_rate: float
    effective_date: date


# ── Calendars & Holidays ───────────────────────────────────────────────

@router.post("/calendars", response_model=CalendarOut, status_code=201)
def create_calendar(
    payload: CalendarCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update")),
):
    cal = HolidayCalendar(**payload.model_dump())
    db.add(cal)
    db.commit()
    db.refresh(cal)
    log_audit(db, user=current_user, action="holiday_calendar_created", entity="holiday_calendar",
              entity_id=cal.id, result=AuditResult.SUCCESS, request=request)
    return cal


@router.get("/calendars", response_model=list[CalendarOut])
def list_calendars(
    country_code: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(HolidayCalendar).filter(HolidayCalendar.is_active == True)
    if country_code:
        q = q.filter(HolidayCalendar.country_code == country_code.upper())
    if year:
        q = q.filter(HolidayCalendar.year == year)
    return q.all()


@router.post("/calendars/{calendar_id}/holidays", response_model=HolidayOut, status_code=201)
def add_holiday(
    calendar_id: str,
    payload: HolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update")),
):
    cal = db.query(HolidayCalendar).filter(HolidayCalendar.id == calendar_id).first()
    if not cal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Calendar not found")

    holiday = Holiday(calendar_id=calendar_id, **payload.model_dump())
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.get("/calendars/{calendar_id}/holidays", response_model=list[HolidayOut])
def list_calendar_holidays(
    calendar_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Holiday).filter(Holiday.calendar_id == calendar_id).order_by(Holiday.date).all()


# ── Currency Rates ──────────────────────────────────────────────────────

@router.post("/currencies/rates", status_code=201)
def upsert_currency_rate(
    payload: CurrencyRateUpsert,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stipends:create")),
):
    rate = CurrencyRate(
        from_currency=payload.from_currency.upper(),
        to_currency=payload.to_currency.upper(),
        exchange_rate=payload.exchange_rate,
        effective_date=payload.effective_date,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return {"id": rate.id, "pair": f"{rate.from_currency}/{rate.to_currency}", "rate": rate.exchange_rate}


@router.get("/currencies/convert")
def convert_currency(
    from_currency: str,
    to_currency: str,
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from_c = from_currency.upper()
    to_c = to_currency.upper()
    if from_c == to_c:
        return {"from": from_c, "to": to_c, "original_amount": amount, "converted_amount": amount, "rate": 1.0}

    rate_rec = db.query(CurrencyRate).filter(
        CurrencyRate.from_currency == from_c,
        CurrencyRate.to_currency == to_c,
    ).order_by(CurrencyRate.effective_date.desc()).first()

    if not rate_rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Exchange rate not found for {from_c} to {to_c}")

    converted = round(amount * rate_rec.exchange_rate, 2)
    return {
        "from": from_c,
        "to": to_c,
        "original_amount": amount,
        "converted_amount": converted,
        "rate": rate_rec.exchange_rate,
        "effective_date": rate_rec.effective_date.isoformat(),
    }
