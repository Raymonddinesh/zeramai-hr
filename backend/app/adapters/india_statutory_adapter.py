"""
India Statutory Compliance Adapter Engine.
Provides configuration-driven, effective-dated, state-aware calculation
for EPF, ESI, Professional Tax (PT), and TDS (Income Tax).
"""
from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models_statutory import (
    StatutoryAuthority,
    StatutoryScheme,
    StatutoryRule,
    StatutoryApplicability,
    TaxDeclaration,
    TaxRegime,
)
from app.models import Person, Engagement, SalaryStructure


class IndiaStatutoryAdapter:
    """Base adapter for India statutory calculations.
    Determines applicable rules based on effective dates, tenant, legal entity, and state.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_applicable_rules(
        self,
        scheme: StatutoryScheme,
        as_of: date,
        tenant_id: Optional[str] = None,
        legal_entity_id: Optional[str] = None,
        state: Optional[str] = None,
        person_id: Optional[str] = None,
    ) -> List[StatutoryRule]:
        """Fetch active StatutoryRule records matching the scheme, effective date, and scope."""
        query = self.db.query(StatutoryRule).filter(
            StatutoryRule.scheme == scheme,
            StatutoryRule.is_active == True,
            StatutoryRule.effective_from <= as_of,
            (StatutoryRule.effective_to == None) | (StatutoryRule.effective_to >= as_of),
        )
        if tenant_id:
            query = query.filter(StatutoryRule.tenant_id == tenant_id)
        if legal_entity_id:
            query = query.filter(StatutoryRule.legal_entity_id == legal_entity_id)
        if state:
            query = query.filter(
                (StatutoryRule.state == None) | (StatutoryRule.state == state) | (StatutoryRule.state == "")
            )

        rules = query.order_by(StatutoryRule.effective_from.desc()).all()
        return rules


class EPFAdapter(IndiaStatutoryAdapter):
    """EPF (Employee Provident Fund) Statutory Calculation Adapter.
    Supports employee contribution, employer contribution, wage ceiling, and administrative charges.
    """

    def calculate(
        self,
        person_id: str,
        as_of: date,
        basic_wage: float,
        gross_wage: float = 0.0,
        tenant_id: Optional[str] = None,
        legal_entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        rules = self.get_applicable_rules(
            scheme=StatutoryScheme.EPF,
            as_of=as_of,
            tenant_id=tenant_id,
            legal_entity_id=legal_entity_id,
            person_id=person_id,
        )

        cfg: Dict[str, Any] = {}
        rule_id = None
        rule_version = "default_epf_v1"

        if rules:
            rule = rules[0]
            cfg = rule.config or {}
            rule_id = rule.id
            rule_version = f"{rule.id}_{rule.effective_from.isoformat()}"

        # Standard Indian EPF defaults if not overridden in rule config:
        # Employee rate: 12%
        # Employer rate: 12% (EPS 8.33%, EPF 3.67%)
        # Statutory ceiling: ₹15,000 / month
        emp_rate = float(cfg.get("employee_rate", 12.0))
        empr_rate = float(cfg.get("employer_rate", 12.0))
        wage_ceiling = cfg.get("wage_ceiling", 15000.0)
        apply_ceiling = cfg.get("apply_ceiling", True)

        if apply_ceiling and wage_ceiling is not None:
            epf_wage = min(float(basic_wage), float(wage_ceiling))
        else:
            epf_wage = float(basic_wage)

        emp_deduction = round(epf_wage * (emp_rate / 100.0), 2)
        empr_contrib = round(epf_wage * (empr_rate / 100.0), 2)

        eps_rate = float(cfg.get("eps_rate", 8.33))
        eps_ceiling = float(cfg.get("eps_ceiling", 15000.0))
        eps_wage = min(epf_wage, eps_ceiling)
        eps_contrib = round(eps_wage * (eps_rate / 100.0), 2)
        epf_diff = round(empr_contrib - eps_contrib, 2)

        edli_rate = float(cfg.get("edli_rate", 0.5))
        admin_rate = float(cfg.get("admin_rate", 0.5))
        edli_contrib = round(eps_wage * (edli_rate / 100.0), 2)
        admin_charges = round(epf_wage * (admin_rate / 100.0), 2)

        total_statutory = emp_deduction + empr_contrib + edli_contrib + admin_charges

        return {
            "scheme": "epf",
            "epf_wage": epf_wage,
            "employee_deduction": emp_deduction,
            "employer_contribution": empr_contrib,
            "total_statutory_amount": total_statutory,
            "breakdown": {
                "employee_epf": emp_deduction,
                "employer_epf_difference": epf_diff,
                "employer_eps": eps_contrib,
                "edli": edli_contrib,
                "admin_charges": admin_charges,
            },
            "rule_id": rule_id,
            "rule_version": rule_version,
            "effective_as_of": as_of.isoformat(),
        }


class ESIAdapter(IndiaStatutoryAdapter):
    """ESI (Employees' State Insurance) Statutory Calculation Adapter.
    Applicable when monthly gross wages <= statutory wage ceiling (₹21,000 / month).
    """

    def calculate(
        self,
        person_id: str,
        as_of: date,
        gross_wage: float,
        tenant_id: Optional[str] = None,
        legal_entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        rules = self.get_applicable_rules(
            scheme=StatutoryScheme.ESI,
            as_of=as_of,
            tenant_id=tenant_id,
            legal_entity_id=legal_entity_id,
            person_id=person_id,
        )

        cfg: Dict[str, Any] = {}
        rule_id = None
        rule_version = "default_esi_v1"

        if rules:
            rule = rules[0]
            cfg = rule.config or {}
            rule_id = rule.id
            rule_version = f"{rule.id}_{rule.effective_from.isoformat()}"

        # Standard Indian ESI rules:
        # Wage ceiling: ₹21,000 / month
        # Employee rate: 0.75%
        # Employer rate: 3.25%
        wage_ceiling = float(cfg.get("wage_ceiling", 21000.0))
        emp_rate = float(cfg.get("employee_rate", 0.75))
        empr_rate = float(cfg.get("employer_rate", 3.25))

        gross = float(gross_wage)
        is_eligible = gross <= wage_ceiling

        if not is_eligible:
            return {
                "scheme": "esi",
                "is_eligible": False,
                "gross_wage": gross,
                "employee_deduction": 0.0,
                "employer_contribution": 0.0,
                "total_statutory_amount": 0.0,
                "breakdown": {"employee": 0.0, "employer": 0.0},
                "rule_id": rule_id,
                "rule_version": rule_version,
                "effective_as_of": as_of.isoformat(),
                "note": f"Gross wage ₹{gross} exceeds statutory ceiling ₹{wage_ceiling}",
            }

        emp_deduction = round(gross * (emp_rate / 100.0), 2)
        empr_contrib = round(gross * (empr_rate / 100.0), 2)
        total = emp_deduction + empr_contrib

        return {
            "scheme": "esi",
            "is_eligible": True,
            "gross_wage": gross,
            "employee_deduction": emp_deduction,
            "employer_contribution": empr_contrib,
            "total_statutory_amount": total,
            "breakdown": {
                "employee": emp_deduction,
                "employer": empr_contrib,
            },
            "rule_id": rule_id,
            "rule_version": rule_version,
            "effective_as_of": as_of.isoformat(),
        }


class ProfessionalTaxAdapter(IndiaStatutoryAdapter):
    """Professional Tax (PT) Statutory Calculation Adapter.
    State-configurable slabs based on monthly gross salary.
    """

    def calculate(
        self,
        person_id: str,
        as_of: date,
        gross_wage: float,
        state: Optional[str] = "Karnataka",
        tenant_id: Optional[str] = None,
        legal_entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        rules = self.get_applicable_rules(
            scheme=StatutoryScheme.PROFESSIONAL_TAX,
            as_of=as_of,
            tenant_id=tenant_id,
            legal_entity_id=legal_entity_id,
            state=state,
            person_id=person_id,
        )

        cfg: Dict[str, Any] = {}
        rule_id = None
        rule_version = "default_pt_v1"

        if rules:
            rule = rules[0]
            cfg = rule.config or {}
            rule_id = rule.id
            rule_version = f"{rule.id}_{rule.effective_from.isoformat()}"

        gross = float(gross_wage)
        slabs = cfg.get("slabs")

        # Configurable state slabs fallback
        if not slabs:
            state_lower = (state or "").lower()
            if "karnataka" in state_lower:
                slabs = [
                    {"min": 0, "max": 14999.99, "tax": 0.0},
                    {"min": 15000, "max": None, "tax": 200.0},
                ]
            elif "maharashtra" in state_lower:
                # Men vs women or general slab:
                slabs = [
                    {"min": 0, "max": 7500.0, "tax": 0.0},
                    {"min": 7500.01, "max": 10000.0, "tax": 175.0},
                    {"min": 10000.01, "max": None, "tax": 200.0},
                ]
            elif "tamil" in state_lower:
                slabs = [
                    {"min": 0, "max": 21000.0, "tax": 0.0},
                    {"min": 21000.01, "max": 30000.0, "tax": 100.0},
                    {"min": 30000.01, "max": 45000.0, "tax": 235.0},
                    {"min": 45000.01, "max": None, "tax": 208.0},
                ]
            else:
                slabs = [
                    {"min": 0, "max": 15000.0, "tax": 0.0},
                    {"min": 15000.01, "max": None, "tax": 200.0},
                ]

        pt_amount = 0.0
        for slab in slabs:
            s_min = float(slab.get("min", 0))
            s_max = slab.get("max")
            s_tax = float(slab.get("tax", 0.0))
            if gross >= s_min and (s_max is None or gross <= float(s_max)):
                pt_amount = s_tax
                break

        return {
            "scheme": "professional_tax",
            "state": state,
            "gross_wage": gross,
            "employee_deduction": pt_amount,
            "employer_contribution": 0.0,
            "total_statutory_amount": pt_amount,
            "slabs_applied": slabs,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "effective_as_of": as_of.isoformat(),
        }


class TDSAdapter(IndiaStatutoryAdapter):
    """TDS / Income Tax Statutory Calculation Adapter.
    Calculates monthly withholding tax based on tax regime (New vs Old),
    annual projected taxable salary, standard deduction, and declarations.
    """

    def calculate(
        self,
        person_id: str,
        as_of: date,
        monthly_gross: float,
        annual_ctc: Optional[float] = None,
        financial_year: Optional[str] = "2026-2027",
        tenant_id: Optional[str] = None,
        legal_entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        rules = self.get_applicable_rules(
            scheme=StatutoryScheme.TDS,
            as_of=as_of,
            tenant_id=tenant_id,
            legal_entity_id=legal_entity_id,
            person_id=person_id,
        )

        cfg: Dict[str, Any] = {}
        rule_id = None
        rule_version = "default_tds_v1"

        if rules:
            rule = rules[0]
            cfg = rule.config or {}
            rule_id = rule.id
            rule_version = f"{rule.id}_{rule.effective_from.isoformat()}"

        # Fetch employee's submitted or verified tax declaration
        decl_query = self.db.query(TaxDeclaration).filter(
            TaxDeclaration.person_id == person_id,
            TaxDeclaration.financial_year == financial_year,
        )
        if tenant_id:
            decl_query = decl_query.filter(TaxDeclaration.tenant_id == tenant_id)
        decl = decl_query.first()

        regime = decl.regime if decl else TaxRegime.NEW
        # Annual income computation
        projected_annual = annual_ctc or (float(monthly_gross) * 12.0)

        # Standard deduction: ₹75,000 for New Regime (FY 24-25 onwards) / ₹50,000 Old Regime
        if regime == TaxRegime.NEW:
            std_deduction = float(cfg.get("standard_deduction_new", 75000.0))
            declared_deductions = 0.0  # Exemptions mostly not applicable under New Regime
        else:
            std_deduction = float(cfg.get("standard_deduction_old", 50000.0))
            declared_deductions = 0.0
            if decl and decl.deductions_json:
                for item in decl.deductions_json:
                    declared_deductions += float(item.get("amount", 0.0))

        net_taxable = max(0.0, projected_annual - std_deduction - declared_deductions)

        # Slab calculation for New Regime (Section 115BAC):
        # 0 - 3,00,000: Nil
        # 3,00,001 - 7,00,000: 5%
        # 7,00,001 - 10,00,000: 10%
        # 10,00,001 - 12,00,000: 15%
        # 12,00,001 - 15,00,000: 20%
        # > 15,00,000: 30%
        # Full rebate under 87A for net taxable up to 7,00,000
        annual_tax = 0.0
        if regime == TaxRegime.NEW:
            if net_taxable <= 700000.0:
                annual_tax = 0.0  # 87A rebate applies
            else:
                rem = net_taxable
                # 0 - 3L: 0
                rem -= 300000.0
                if rem > 0:
                    tier = min(rem, 400000.0)
                    annual_tax += tier * 0.05
                    rem -= tier
                if rem > 0:
                    tier = min(rem, 300000.0)
                    annual_tax += tier * 0.10
                    rem -= tier
                if rem > 0:
                    tier = min(rem, 200000.0)
                    annual_tax += tier * 0.15
                    rem -= tier
                if rem > 0:
                    tier = min(rem, 300000.0)
                    annual_tax += tier * 0.20
                    rem -= tier
                if rem > 0:
                    annual_tax += rem * 0.30

                # 4% Health & Education Cess
                annual_tax += annual_tax * 0.04
        else:
            # Old regime general calculation
            if net_taxable <= 500000.0:
                annual_tax = 0.0
            else:
                rem = net_taxable - 250000.0
                if rem > 0:
                    tier = min(rem, 250000.0)
                    annual_tax += tier * 0.05
                    rem -= tier
                if rem > 0:
                    tier = min(rem, 500000.0)
                    annual_tax += tier * 0.20
                    rem -= tier
                if rem > 0:
                    annual_tax += rem * 0.30
                annual_tax += annual_tax * 0.04

        monthly_tds = round(annual_tax / 12.0, 2)

        return {
            "scheme": "tds",
            "regime": regime.value if hasattr(regime, "value") else str(regime),
            "projected_annual_gross": projected_annual,
            "standard_deduction": std_deduction,
            "declared_deductions": declared_deductions,
            "net_taxable_income": round(net_taxable, 2),
            "projected_annual_tax": round(annual_tax, 2),
            "monthly_tds_deduction": monthly_tds,
            "employee_deduction": monthly_tds,
            "employer_contribution": 0.0,
            "total_statutory_amount": monthly_tds,
            "financial_year": financial_year,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "effective_as_of": as_of.isoformat(),
        }
