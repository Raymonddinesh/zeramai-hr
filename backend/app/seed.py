"""
Run with: python -m app.seed
Creates one login per role so you can exercise RBAC immediately.
Passwords are dev-only placeholders — change before any shared/staging use.
"""
from decimal import Decimal
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
    from app.models import Role, Person
    try:
        # Load all roles by name
        roles_by_name = {r.name: r for r in db.query(Role).all()}
        
        for email, password, role_enum in DEMO_USERS:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email, hashed_password=hash_password(password), role=role_enum)
                db.add(user)
                db.flush()
            # Ensure a Person exists and link
            if not user.person_id:
                person = db.query(Person).filter(Person.email == email).first()
                if not person:
                    person = Person(full_name=email.split('@')[0].replace('.', ' ').title(), email=email)
                    db.add(person)
                    db.flush()
                user.person_id = person.id
                db.flush()
            
            # Map legacy enum role to Role entity (enum names are lowercase strings like 'super_admin' or 'employee' in UserRole)
            role_name_str = role_enum.name  # SUPER_ADMIN
            if role_name_str in roles_by_name:
                role_obj = roles_by_name[role_name_str]
                if role_obj not in user.roles:
                    user.roles.append(role_obj)
            
        # Ensure canonical manager -> employee Engagement relationship exists
        emp_user = db.query(User).filter(User.email == "employee@example.com").first()
        mgr_user = db.query(User).filter(User.email == "manager@zeramai.com").first()
        if emp_user and mgr_user and emp_user.person_id:
            from app.models import Engagement, EngagementType, EngagementStatus
            from datetime import date, datetime
            eng = db.query(Engagement).filter(Engagement.person_id == emp_user.person_id).first()
            if not eng:
                eng = Engagement(
                    person_id=emp_user.person_id,
                    reporting_manager_id=mgr_user.id,
                    engagement_type=EngagementType.FULL_TIME_EMPLOYEE,
                    designation="Software Engineer",
                    department="Engineering",
                    work_location="Bangalore",
                    start_date=date(2026, 1, 1),
                    status=EngagementStatus.ACTIVE,
                )
                db.add(eng)
            else:
                eng.reporting_manager_id = mgr_user.id

        # Seed standard Module 14 Integration Catalog Providers
        from app.models_integrations import IntegrationProvider, ProviderCategory
        catalog_providers = [
            {
                "code": "entra_id",
                "name": "Microsoft Entra ID",
                "category": ProviderCategory.IDENTITY.value,
                "provider_type": "SSO_SCIM",
                "description": "Enterprise SSO and SCIM 2.0 provisioning via Microsoft Entra ID / Azure AD.",
            },
            {
                "code": "google_workspace",
                "name": "Google Workspace",
                "category": ProviderCategory.IDENTITY.value,
                "provider_type": "SSO_DIRECTORY",
                "description": "Google Cloud Identity and Workspace user directory sync.",
            },
            {
                "code": "slack",
                "name": "Slack",
                "category": ProviderCategory.COMMUNICATION.value,
                "provider_type": "WEBHOOK_BOT",
                "description": "Slack automated employee onboarding alerts and HR bot notifications.",
            },
            {
                "code": "generic_webhook",
                "name": "Generic HTTP Webhook",
                "category": ProviderCategory.COMMUNICATION.value,
                "provider_type": "WEBHOOK",
                "description": "Outbound HTTP webhook subscriptions with HMAC-SHA256 signature verification.",
            },
        ]
        for p_data in catalog_providers:
            existing_p = db.query(IntegrationProvider).filter(IntegrationProvider.code == p_data["code"]).first()
            if not existing_p:
                p_obj = IntegrationProvider(
                    tenant_id=None,
                    name=p_data["name"],
                    code=p_data["code"],
                    category=p_data["category"],
                    provider_type=p_data["provider_type"],
                    description=p_data["description"],
                    enabled=True,
                )
                db.add(p_obj)

        # Module 15: Data Governance Catalog and Policies
        from app.models_governance import (
            DataClassification,
            RetentionPolicy,
            BackupPolicy,
            DRPolicy,
            DataResidencyPolicy,
            SensitivityLevel,
        )
        from app.models_v3 import Tenant

        default_tenant = db.query(Tenant).first()
        if not default_tenant:
            default_tenant = Tenant(name="Zeramai Enterprise", domain="zeramai.com")
            db.add(default_tenant)
            db.flush()
        tenant_id = default_tenant.id

        from app.models_v3 import LegalEntity
        default_le = db.query(LegalEntity).filter(LegalEntity.tenant_id == tenant_id).first()
        if not default_le:
            default_le = LegalEntity(
                tenant_id=tenant_id,
                name="Zeramai Technologies Private Limited",
                registration_number="U72900KA2024PTC123456",
                tax_id="29ABCDE1234F1Z5",
                country_code="IN",
                default_currency="INR",
                is_active=True,
            )
            db.add(default_le)
            db.flush()
        legal_entity_id = default_le.id

        for p in db.query(Person).all():
            if hasattr(p, "tenant_id") and not p.tenant_id:
                p.tenant_id = tenant_id

        default_classifications = [
            ("PUBLIC", "Public Data", "Data suitable for public dissemination", SensitivityLevel.PUBLIC.value, 365),
            ("INTERNAL", "Internal Operational", "Internal business data with limited sensitivity", SensitivityLevel.INTERNAL.value, 730),
            ("CONFIDENTIAL", "Confidential HR / Financial", "Employee records, salary details, and contracts", SensitivityLevel.CONFIDENTIAL.value, 2555),
            ("RESTRICTED", "Restricted Statutory / PII", "Statutory tax filings, Aadhaar/PAN, banking details", SensitivityLevel.RESTRICTED.value, 2555),
            ("HIGHLY_RESTRICTED", "Highly Restricted Secrets", "Cryptographic keys, master credentials, credentials", SensitivityLevel.HIGHLY_RESTRICTED.value, 90),
        ]
        for code, name, desc, sens, ret_days in default_classifications:
            existing_c = db.query(DataClassification).filter(DataClassification.code == code).first()
            if not existing_c:
                c_obj = DataClassification(
                    tenant_id=None,
                    code=code,
                    name=name,
                    description=desc,
                    sensitivity_level=sens,
                    default_retention_days=ret_days,
                    enabled=True,
                )
                db.add(c_obj)

        # Statutory Retention Policy
        admin_user = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        admin_id = admin_user.id if admin_user else "admin-user"

        existing_rp = db.query(RetentionPolicy).filter(
            RetentionPolicy.tenant_id == tenant_id,
            RetentionPolicy.record_type == "PAYROLL"
        ).first()
        if not existing_rp:
            rp = RetentionPolicy(
                tenant_id=tenant_id,
                name="Statutory Payroll & Tax Retention (7 Years)",
                description="Mandatory statutory retention of wage records and tax withholdings under Income Tax Act 1961 Section 44AA and EPF Act.",
                record_type="PAYROLL",
                retention_period_days=2555,
                archive_after_days=365,
                deletion_after_days=None,  # Preserved
                legal_basis="Income Tax Act 1961 Section 44AA; EPF & MP Act 1952",
                jurisdiction="IN",
                enabled=True,
                created_by=admin_id,
            )
            db.add(rp)

        # Backup Policy
        existing_bp = db.query(BackupPolicy).filter(BackupPolicy.tenant_id == tenant_id).first()
        if not existing_bp:
            bp = BackupPolicy(
                tenant_id=tenant_id,
                name="Standard Daily Encrypted Backup",
                frequency="DAILY",
                retention_days=30,
                encryption_required=True,
                offsite_required=True,
                cross_region_required=True,
                enabled=True,
            )
            db.add(bp)

        # DR Policy
        existing_dr = db.query(DRPolicy).filter(DRPolicy.tenant_id == tenant_id).first()
        if not existing_dr:
            dr = DRPolicy(
                tenant_id=tenant_id,
                name="Core HR & Payroll Disaster Recovery Policy",
                rpo_minutes=60,
                rto_minutes=240,
                primary_region="IN-SOUTH",
                recovery_region="IN-WEST",
                priority="BUSINESS_CRITICAL",
                enabled=True,
            )
            db.add(dr)

        # Data Residency Policy
        existing_res = db.query(DataResidencyPolicy).filter(DataResidencyPolicy.tenant_id == tenant_id).first()
        if not existing_res:
            dres = DataResidencyPolicy(
                tenant_id=tenant_id,
                data_category="EMPLOYEE_PII_AND_PAYROLL",
                allowed_regions=["IN-CENTRAL", "IN-SOUTH", "IN-WEST"],
                primary_region="IN-CENTRAL",
                cross_border_transfer_allowed=False,
                transfer_basis="India DPDP Act 2023 Sovereign Data Protection Mandate",
                enabled=True,
            )
            db.add(dres)

        # Module 16: Finance & Workforce Cost Default Seeds
        from app.models_finance import (
            FinancialDimension, FinancialDimensionValue, GLAccount, GLMapping,
            GLAccountType, GLTransactionType
        )
        from app.models_v3 import CostCenter
        from datetime import date

        # Financial Dimensions
        dim_dept = db.query(FinancialDimension).filter(FinancialDimension.tenant_id == tenant_id, FinancialDimension.code == "DEPARTMENT").first()
        if not dim_dept:
            dim_dept = FinancialDimension(
                tenant_id=tenant_id,
                code="DEPARTMENT",
                name="Department",
                dimension_type="DEPARTMENT",
                description="Core organizational department dimension",
                active=True
            )
            db.add(dim_dept)
            db.flush()
            val_eng = FinancialDimensionValue(
                tenant_id=tenant_id,
                dimension_id=dim_dept.id,
                code="DEPT_ENG",
                name="Software Engineering",
                active=True
            )
            val_fin = FinancialDimensionValue(
                tenant_id=tenant_id,
                dimension_id=dim_dept.id,
                code="DEPT_FIN",
                name="Corporate Finance",
                active=True
            )
            db.add_all([val_eng, val_fin])

        # Cost Centers
        cc_eng = db.query(CostCenter).filter(CostCenter.tenant_id == tenant_id, CostCenter.code == "CC-ENG-01").first()
        if not cc_eng:
            cc_eng = CostCenter(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                code="CC-ENG-01",
                name="Engineering Core Cost Center",
                description="R&D, Platform, Infrastructure and Product Development",
                currency="INR",
                active=True
            )
            db.add(cc_eng)
            cc_ops = CostCenter(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                code="CC-OPS-01",
                name="Corporate & Operations Cost Center",
                description="General and Administrative, People Operations, Executive",
                currency="INR",
                active=True
            )
            db.add(cc_ops)

        # GL Accounts
        gl_defs = [
            ("50100", "Salaries & Wages Expense", GLAccountType.EXPENSE.value),
            ("50200", "Employer Statutory Contribution Expense", GLAccountType.EXPENSE.value),
            ("50300", "Performance Bonus & Variable Pay", GLAccountType.EXPENSE.value),
            ("50400", "Employee Benefits & Wellness Expense", GLAccountType.EXPENSE.value),
            ("20100", "Net Salaries Payable", GLAccountType.LIABILITY.value),
            ("20200", "Statutory Withholdings Payable (TDS/EPF/PT)", GLAccountType.LIABILITY.value),
            ("20300", "Employer Statutory Contributions Payable", GLAccountType.LIABILITY.value),
        ]
        gl_map = {}
        for code, name, acct_type in gl_defs:
            acct = db.query(GLAccount).filter(GLAccount.tenant_id == tenant_id, GLAccount.code == code).first()
            if not acct:
                acct = GLAccount(
                    tenant_id=tenant_id,
                    code=code,
                    name=name,
                    account_type=acct_type,
                    active=True
                )
                db.add(acct)
                db.flush()
            gl_map[code] = acct

        # GL Mappings
        mapping_defs = [
            (GLTransactionType.SALARY.value, "50100", "20100"),
            (GLTransactionType.BONUS.value, "50300", "20100"),
            (GLTransactionType.EMPLOYER_EPF.value, "50200", "20300"),
            (GLTransactionType.EMPLOYER_ESI.value, "50200", "20300"),
            (GLTransactionType.TDS.value, "50100", "20200"),
            (GLTransactionType.PROFESSIONAL_TAX.value, "50100", "20200"),
            (GLTransactionType.BENEFITS.value, "50400", "20100"),
        ]
        for tx_type, dr_code, cr_code in mapping_defs:
            existing_m = db.query(GLMapping).filter(
                GLMapping.tenant_id == tenant_id,
                GLMapping.transaction_type == tx_type
            ).first()
            if not existing_m:
                dr_id = gl_map[dr_code].id if dr_code and dr_code in gl_map else None
                cr_id = gl_map[cr_code].id if cr_code and cr_code in gl_map else None
                if dr_id and cr_id:
                    m_obj = GLMapping(
                        tenant_id=tenant_id,
                        transaction_type=tx_type,
                        debit_account_id=dr_id,
                        credit_account_id=cr_id,
                        effective_from=date(2026, 1, 1),
                        active=True
                    )
                    db.add(m_obj)

        # Seed sample balanced payroll journal
        from app.models_finance import PayrollJournal, PayrollJournalLine, PayrollJournalStatus
        pj = db.query(PayrollJournal).filter(PayrollJournal.tenant_id == tenant_id).first()
        if not pj:
            pj = PayrollJournal(
                tenant_id=tenant_id,
                journal_number="PJ-2026-03-SEED",
                accounting_date=date(2026, 3, 31),
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
                currency="INR",
                status=PayrollJournalStatus.POSTED.value,
                total_debit=500000.0,
                total_credit=500000.0,
            )
            db.add(pj)
            db.flush()
            dr_acct = gl_map.get("50100")
            cr_acct = gl_map.get("20100")
            if dr_acct and cr_acct:
                l1 = PayrollJournalLine(
                    tenant_id=tenant_id,
                    journal_id=pj.id,
                    account_id=dr_acct.id,
                    cost_center_id=cc_eng.id if cc_eng else None,
                    description="Gross Salaries & Wages - March 2026",
                    debit=500000.0,
                    credit=0.0,
                )
                l2 = PayrollJournalLine(
                    tenant_id=tenant_id,
                    journal_id=pj.id,
                    account_id=cr_acct.id,
                    cost_center_id=cc_eng.id if cc_eng else None,
                    description="Net Wages Payable - March 2026",
                    debit=0.0,
                    credit=500000.0,
                )
                db.add_all([l1, l2])

        # Seed Module 17 Workforce Planning defaults
        from app.models_workforce_planning import (
            OrganizationUnit, Position, PositionAssignment, Skill, SkillLevel,
            CriticalRole, SuccessionPlan, SuccessionCandidate, TalentPool, TalentPoolMember,
            HeadcountPlan, HeadcountPlanLine, WorkforceScenario, WorkforceScenarioLine,
            OrgUnitType, PositionStatus, PositionAssignmentType, HeadcountPlanStatus,
            RoleCriticality, SuccessionStatus, ReadinessLevel, TalentPoolStatus,
        )

        ou_corp = db.query(OrganizationUnit).filter(OrganizationUnit.tenant_id == tenant_id, OrganizationUnit.code == "CORP").first()
        if not ou_corp:
            ou_corp = OrganizationUnit(
                tenant_id=tenant_id,
                code="CORP",
                name="Corporate Headquarters",
                unit_type=OrgUnitType.COMPANY.value,
                active=True,
                effective_from=date(2026, 1, 1),
            )
            db.add(ou_corp)
            db.flush()

        ou_eng = db.query(OrganizationUnit).filter(OrganizationUnit.tenant_id == tenant_id, OrganizationUnit.code == "ENG-DIV").first()
        if not ou_eng:
            ou_eng = OrganizationUnit(
                tenant_id=tenant_id,
                parent_id=ou_corp.id,
                code="ENG-DIV",
                name="Engineering Division",
                unit_type=OrgUnitType.DIVISION.value,
                active=True,
                effective_from=date(2026, 1, 1),
            )
            db.add(ou_eng)
            db.flush()

        pos_lead = db.query(Position).filter(Position.tenant_id == tenant_id, Position.position_code == "POS-ENG-001").first()
        if not pos_lead:
            pos_lead = Position(
                tenant_id=tenant_id,
                organization_unit_id=ou_eng.id,
                position_code="POS-ENG-001",
                title="Lead Platform Architect",
                job_family="Engineering",
                job_level="Staff / L5",
                employment_type="FULL_TIME",
                location="Bengaluru",
                status=PositionStatus.PARTIALLY_FILLED.value,
                headcount_capacity=2.0,
                filled_count=1.0,
                budgeted_cost=3600000.0,
                currency="INR",
                effective_from=date(2026, 1, 1),
            )
            db.add(pos_lead)
            db.flush()

        # Seed Skills
        skill_py = db.query(Skill).filter(Skill.code == "SKILL-PYTHON").first()
        if not skill_py:
            skill_py = Skill(
                tenant_id=tenant_id,
                code="SKILL-PYTHON",
                name="Python Architecture & FastAPIs",
                category="TECHNICAL",
                description="Core backend language proficiency with async systems and SQLAlchemy",
                active=True,
            )
            db.add(skill_py)
            db.flush()
            for l_code, l_name, l_rank in [("L1", "Novice", 1), ("L2", "Intermediate", 2), ("L3", "Advanced", 3), ("L4", "Expert", 4)]:
                db.add(SkillLevel(skill_id=skill_py.id, code=l_code, name=l_name, rank=l_rank))

        # Seed Critical Role
        cr_lead = db.query(CriticalRole).filter(CriticalRole.tenant_id == tenant_id, CriticalRole.position_id == pos_lead.id).first()
        if not cr_lead:
            cr_lead = CriticalRole(
                tenant_id=tenant_id,
                position_id=pos_lead.id,
                criticality=RoleCriticality.HIGH.value,
                business_impact="Core platform stability and architectural continuity",
                replacement_difficulty="HIGH",
                vacancy_risk="MEDIUM",
                status="ACTIVE",
            )
            db.add(cr_lead)
            db.flush()

        # Seed Headcount Plan
        hp = db.query(HeadcountPlan).filter(HeadcountPlan.tenant_id == tenant_id, HeadcountPlan.fiscal_year == "2026-2027").first()
        if not hp:
            hp = HeadcountPlan(
                tenant_id=tenant_id,
                name="FY2026-27 Strategic Growth Plan",
                fiscal_year="2026-2027",
                currency="INR",
                status=HeadcountPlanStatus.APPROVED.value,
                created_by=admin_user.id,
            )
            db.add(hp)
            db.flush()
            db.add(HeadcountPlanLine(
                tenant_id=tenant_id,
                plan_id=hp.id,
                organization_unit_id=ou_eng.id,
                position_id=pos_lead.id,
                job_family="Engineering",
                job_level="Staff / L5",
                month="2026-04",
                planned_headcount=2.0,
                planned_hires=1.0,
                planned_exits=0.0,
                planned_cost=300000.0,
                currency="INR",
            ))

        # Seed Module 18: Learning, Skills & Career Development
        from app.models_learning import (
            TrainingProvider, LearningCourse, LearningModule, CourseContent,
            LearningPath, Certification, CareerFramework, CareerLevel,
            MentoringProgram, CourseLifecycleStatus
        )

        provider = db.query(TrainingProvider).filter(TrainingProvider.tenant_id == tenant_id, TrainingProvider.name == "Zeramai Enterprise Academy").first()
        if not provider:
            provider = TrainingProvider(
                tenant_id=tenant_id,
                name="Zeramai Enterprise Academy",
                provider_type="INTERNAL",
                website="https://academy.zeramai.internal",
                contact_reference="academy@zeramai.com",
                active=True,
            )
            db.add(provider)
            db.flush()

        course = db.query(LearningCourse).filter(LearningCourse.tenant_id == tenant_id, LearningCourse.course_code == "CRS-ARCH-101").first()
        if not course:
            course = LearningCourse(
                tenant_id=tenant_id,
                course_code="CRS-ARCH-101",
                title="Enterprise Cloud Architecture & Security",
                description="Comprehensive masterclass on designing highly available, secure multi-tenant cloud platforms.",
                category="TECHNICAL",
                learning_type="COURSE",
                difficulty="ADVANCED",
                duration_minutes=120,
                provider_id=provider.id,
                delivery_mode="ONLINE",
                language="en",
                status=CourseLifecycleStatus.PUBLISHED.value,
                created_by=admin_user.id,
            )
            db.add(course)
            db.flush()

            mod1 = LearningModule(
                course_id=course.id,
                title="Module 1: Principles of Scalable Cloud Design",
                sequence=1,
                duration_minutes=60,
                mandatory=True,
            )
            db.add(mod1)
            db.flush()

            db.add(CourseContent(
                module_id=mod1.id,
                content_type="DOCUMENT",
                title="Architecture Whitepaper & Guidelines",
                duration_minutes=30,
                sequence=1,
                required=True,
            ))

        lp = db.query(LearningPath).filter(LearningPath.tenant_id == tenant_id, LearningPath.name == "Principal Engineering Acceleration").first()
        if not lp:
            lp = LearningPath(
                tenant_id=tenant_id,
                name="Principal Engineering Acceleration",
                description="Curated pathway for senior engineers transitioning to technical leadership.",
                target_role="Staff / Principal Engineer",
                target_job_family="Engineering",
                status=CourseLifecycleStatus.PUBLISHED.value,
                created_by=admin_user.id,
            )
            db.add(lp)
            db.flush()

        cert = db.query(Certification).filter(Certification.tenant_id == tenant_id, Certification.name == "Cloud Architecture Professional").first()
        if not cert:
            cert = Certification(
                tenant_id=tenant_id,
                name="Cloud Architecture Professional",
                issuing_body="Zeramai Architecture Board",
                description="Verified technical mastery in cloud systems and data security.",
                validity_months=24,
                status="ACTIVE",
            )
            db.add(cert)
            db.flush()

        cf = db.query(CareerFramework).filter(CareerFramework.tenant_id == tenant_id, CareerFramework.job_family == "Engineering").first()
        if not cf:
            cf = CareerFramework(
                tenant_id=tenant_id,
                name="Engineering Career Framework",
                job_family="Engineering",
                description="Technical competency and progression standards across software engineering.",
                status="ACTIVE",
            )
            db.add(cf)
            db.flush()

            for seq, (c_code, c_name) in enumerate([("L1", "Associate Engineer"), ("L2", "Software Engineer"), ("L3", "Senior Engineer")]):
                db.add(CareerLevel(
                    tenant_id=tenant_id,
                    framework_id=cf.id,
                    code=c_code,
                    name=c_name,
                    sequence=seq + 1,
                    description=f"{c_name} role expectations and core competencies",
                ))

        mp = db.query(MentoringProgram).filter(MentoringProgram.tenant_id == tenant_id, MentoringProgram.name == "Technical Leadership Mentorship 2026").first()
        if not mp:
            mp = MentoringProgram(
                tenant_id=tenant_id,
                name="Technical Leadership Mentorship 2026",
                description="6-month structured pair mentoring for engineering talent.",
                duration_months=6,
                status="ACTIVE",
            )
            db.add(mp)

        # Module 19: Employee Engagement, Surveys, Recognition & Culture Demo Seeds
        from app.models_engagement import (
            SurveyTemplate, SurveyQuestion, SurveyType, SurveyTemplateStatus,
            SurveyQuestionType, RecognitionProgram, RecognitionType,
            AwardDefinition, CultureInitiative, CultureInitiativeCategory
        )

        st = db.query(SurveyTemplate).filter(SurveyTemplate.tenant_id == tenant_id, SurveyTemplate.name == "Annual Employee Engagement & Culture Survey 2026").first()
        if not st:
            st = SurveyTemplate(
                tenant_id=tenant_id,
                name="Annual Employee Engagement & Culture Survey 2026",
                description="Comprehensive organization-wide survey measuring workplace culture, collaboration, and employee experience.",
                survey_type=SurveyType.ENGAGEMENT,
                status=SurveyTemplateStatus.PUBLISHED,
                estimated_minutes=10,
                anonymous_by_default=True,
                created_by=admin_user.id,
            )
            db.add(st)
            db.flush()

            q1 = SurveyQuestion(
                tenant_id=tenant_id,
                template_id=st.id,
                question_type=SurveyQuestionType.RATING,
                question_text="How satisfied are you with the culture of collaboration and mutual support at Zeramai?",
                category="CULTURE",
                sequence=1,
                required=True,
                anonymous=True,
                scale_min=1,
                scale_max=5,
            )
            q2 = SurveyQuestion(
                tenant_id=tenant_id,
                template_id=st.id,
                question_type=SurveyQuestionType.NPS,
                question_text="How likely are you to recommend Zeramai as an exceptional workplace to peers?",
                category="CULTURE",
                sequence=2,
                required=True,
                anonymous=True,
                scale_min=0,
                scale_max=10,
            )
            q3 = SurveyQuestion(
                tenant_id=tenant_id,
                template_id=st.id,
                question_type=SurveyQuestionType.TEXT,
                question_text="What is one initiative leadership could take to improve work-life balance and growth?",
                category="GENERAL",
                sequence=3,
                required=False,
                anonymous=True,
            )
            db.add_all([q1, q2, q3])

        rp = db.query(RecognitionProgram).filter(RecognitionProgram.tenant_id == tenant_id, RecognitionProgram.name == "Peer Excellence & Core Values Recognition").first()
        if not rp:
            rp = RecognitionProgram(
                tenant_id=tenant_id,
                name="Peer Excellence & Core Values Recognition",
                description="Peer-to-peer appreciation program for demonstrating innovation, collaboration, and integrity.",
                recognition_type=RecognitionType.PEER,
                points_reward=50,
                status="ACTIVE",
            )
            db.add(rp)

        ad = db.query(AwardDefinition).filter(AwardDefinition.tenant_id == tenant_id, AwardDefinition.name == "Annual Culture Champion Award").first()
        if not ad:
            ad = AwardDefinition(
                tenant_id=tenant_id,
                name="Annual Culture Champion Award",
                description="Recognizing team members who significantly enhance workplace inclusion and morale.",
                criteria="Excellence in peer collaboration, mentorship, and company cultural representation.",
                frequency="ANNUAL",
                active=True,
            )
            db.add(ad)

        ci = db.query(CultureInitiative).filter(CultureInitiative.tenant_id == tenant_id, CultureInitiative.name == "Zeramai Community Mentorship & Wellbeing Circle").first()
        if not ci:
            ci = CultureInitiative(
                tenant_id=tenant_id,
                name="Zeramai Community Mentorship & Wellbeing Circle",
                description="Cross-functional community circle focused on mental wellbeing, peer connection, and knowledge exchange.",
                category=CultureInitiativeCategory.WELLBEING,
                owner_user_id=admin_user.id,
                start_date=date.today(),
                status="ACTIVE",
                target_participants=50,
            )
            db.add(ci)

        # Module 20 Seed Data
        from app.models_communications import (
            KnowledgeCategory, KnowledgeArticle, KnowledgeArticleVersion,
            CommunicationTemplate, EmployeeAnnouncement,
            ArticleType, ArticleStatus, ArticleVisibility,
            CommunicationTemplateType, AnnouncementType, AnnouncementPriority, AnnouncementStatus
        )
        kc_hr = db.query(KnowledgeCategory).filter(KnowledgeCategory.tenant_id == tenant_id, KnowledgeCategory.code == "HR-BENEFITS").first()
        if not kc_hr:
            kc_hr = KnowledgeCategory(
                tenant_id=tenant_id,
                code="HR-BENEFITS",
                name="HR, Compensation & Global Benefits",
                description="Company policies, standard operating procedures, and employee benefits guides.",
                display_order=1,
                active=True,
            )
            db.add(kc_hr)
            db.flush()

        kc_eng = db.query(KnowledgeCategory).filter(KnowledgeCategory.tenant_id == tenant_id, KnowledgeCategory.code == "ENG-IT").first()
        if not kc_eng:
            kc_eng = KnowledgeCategory(
                tenant_id=tenant_id,
                code="ENG-IT",
                name="Engineering Architecture & Security",
                description="Developer onboarding, security guidelines, and internal infrastructure references.",
                display_order=2,
                active=True,
            )
            db.add(kc_eng)
            db.flush()

        ka = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.slug == "remote-work-flexibility-guide").first()
        if not ka:
            ka = KnowledgeArticle(
                tenant_id=tenant_id,
                category_id=kc_hr.id,
                title="Workplace Flexibility & Remote Work Policy Guide",
                slug="remote-work-flexibility-guide",
                summary="Guidelines for hybrid working arrangements, core hours, and remote home-office stipends.",
                content_reference="# Workplace Flexibility Guidelines\n\nZeramai supports modern, flexible work arrangements for all team members. Core collaboration hours are 10:00 to 16:00 local time.\n\n### Stipend & Equipment\nFull-time employees are eligible for home setup equipment and internet reimbursement via the Finance portal.",
                article_type=ArticleType.GUIDE,
                status=ArticleStatus.PUBLISHED,
                visibility=ArticleVisibility.ALL_EMPLOYEES,
                owner_user_id=admin_user.id,
                published_at=datetime.utcnow(),
            )
            db.add(ka)
            db.flush()

            ver = KnowledgeArticleVersion(
                tenant_id=tenant_id,
                article_id=ka.id,
                version_number=1,
                title=ka.title,
                content_reference=ka.content_reference,
                change_summary="Initial verified publication",
                created_by=admin_user.id,
                published_at=datetime.utcnow(),
            )
            db.add(ver)

        ct = db.query(CommunicationTemplate).filter(CommunicationTemplate.tenant_id == tenant_id, CommunicationTemplate.name == "Quarterly All-Hands Announcement").first()
        if not ct:
            ct = CommunicationTemplate(
                tenant_id=tenant_id,
                name="Quarterly All-Hands Announcement",
                template_type=CommunicationTemplateType.ANNOUNCEMENT,
                subject_template="Zeramai Enterprise All-Hands — {{quarter}}",
                body_reference="Dear Team,\nPlease join us for our upcoming quarterly all-hands meeting where executive leadership will share business updates and recognize standout contributions.",
                active=True,
                created_by=admin_user.id,
            )
            db.add(ct)

        ea = db.query(EmployeeAnnouncement).filter(EmployeeAnnouncement.tenant_id == tenant_id, EmployeeAnnouncement.title == "Annual Open Enrollment: Global Health & Wellness Benefits").first()
        if not ea:
            ea = EmployeeAnnouncement(
                tenant_id=tenant_id,
                title="Annual Open Enrollment: Global Health & Wellness Benefits",
                summary="The annual benefit election window is now active. Review plan options and dependents by the end of the month.",
                content_reference="# Annual Health & Wellness Benefits Open Enrollment\n\nAll full-time team members are invited to review and submit their insurance, wellness, and retirement contribution choices.",
                announcement_type=AnnouncementType.BENEFITS,
                priority=AnnouncementPriority.HIGH,
                status=AnnouncementStatus.PUBLISHED,
                author_user_id=admin_user.id,
                publish_at=datetime.utcnow(),
                acknowledgement_required=True,
            )
            db.add(ea)

        # Module 21: Global Payroll & Multi-Country Workforce Platform Seeds
        from app.models_global_payroll import (
            PayrollCountry, GlobalPayrollConfiguration, PayrollPayGroup,
            PayrollCalendar, GlobalPayComponent, PayrollExchangeRate,
            EmployeePayrollAssignment, CountryPayrollStatus, PayrollFrequency,
            GlobalPayComponentType, PayrollCalendarStatus, AssignmentPayrollStatus,
            FXRateSource,
        )

        country_data = [
            ("IND", "India", "INR", "Asia/Kolkata", CountryPayrollStatus.PRODUCTION_VALIDATED),
            ("USA", "United States", "USD", "America/New_York", CountryPayrollStatus.FRAMEWORK_READY),
            ("GBR", "United Kingdom", "GBP", "Europe/London", CountryPayrollStatus.FRAMEWORK_READY),
            ("CAN", "Canada", "CAD", "America/Toronto", CountryPayrollStatus.CONFIGURED_ONLY),
            ("AUS", "Australia", "AUD", "Australia/Sydney", CountryPayrollStatus.CONFIGURED_ONLY),
            ("SGP", "Singapore", "SGD", "Asia/Singapore", CountryPayrollStatus.FRAMEWORK_READY),
            ("UAE", "United Arab Emirates", "AED", "Asia/Dubai", CountryPayrollStatus.CONFIGURED_ONLY),
        ]
        created_countries = {}
        for c_code, c_name, c_curr, c_tz, c_status in country_data:
            c_obj = db.query(PayrollCountry).filter(PayrollCountry.tenant_id == tenant_id, PayrollCountry.country_code == c_code).first()
            if not c_obj:
                c_obj = PayrollCountry(
                    tenant_id=tenant_id,
                    country_code=c_code,
                    country_name=c_name,
                    default_currency=c_curr,
                    timezone=c_tz,
                    active=True,
                    payroll_enabled=True,
                    adapter_status=c_status.value,
                )
                db.add(c_obj)
                db.flush()
            created_countries[c_code] = c_obj

        # Global Pay Components
        components_data = [
            ("BASIC", "Basic Salary", GlobalPayComponentType.EARNING, True, True, True),
            ("HRA", "House Rent Allowance", GlobalPayComponentType.EARNING, True, False, True),
            ("SPECIAL_ALLOWANCE", "Special Allowance", GlobalPayComponentType.EARNING, True, False, True),
            ("PERFORMANCE_BONUS", "Performance Bonus", GlobalPayComponentType.EARNING, True, False, False),
            ("EXPENSE_REIMBURSEMENT", "Expense Reimbursement", GlobalPayComponentType.REIMBURSEMENT, False, False, False),
            ("VOLUNTARY_DEDUCTION", "Voluntary Salary Deduction", GlobalPayComponentType.DEDUCTION, False, False, True),
        ]
        for code, name, c_type, taxable, pensionable, recurring in components_data:
            comp_obj = db.query(GlobalPayComponent).filter(GlobalPayComponent.tenant_id == tenant_id, GlobalPayComponent.code == code).first()
            if not comp_obj:
                comp_obj = GlobalPayComponent(
                    tenant_id=tenant_id,
                    code=code,
                    name=name,
                    component_type=c_type.value,
                    taxable=taxable,
                    pensionable=pensionable,
                    recurring=recurring,
                    active=True,
                )
                db.add(comp_obj)

        # Exchange rates
        fx_rates_data = [
            ("USD", "INR", Decimal("83.500000")),
            ("EUR", "INR", Decimal("91.200000")),
            ("GBP", "INR", Decimal("108.500000")),
            ("USD", "AED", Decimal("3.672500")),
            ("USD", "SGD", Decimal("1.345000")),
        ]
        for b_curr, q_curr, rate_val in fx_rates_data:
            fx_obj = db.query(PayrollExchangeRate).filter(
                PayrollExchangeRate.tenant_id == tenant_id,
                PayrollExchangeRate.base_currency == b_curr,
                PayrollExchangeRate.quote_currency == q_curr,
            ).first()
            if not fx_obj:
                fx_obj = PayrollExchangeRate(
                    tenant_id=tenant_id,
                    base_currency=b_curr,
                    quote_currency=q_curr,
                    rate=rate_val,
                    effective_date=date.today(),
                    source=FXRateSource.CONFIGURED.value,
                )
                db.add(fx_obj)

        # India Configuration & Pay Group
        ind_country = created_countries.get("IND")
        if ind_country:
            ind_cfg = db.query(GlobalPayrollConfiguration).filter(
                GlobalPayrollConfiguration.tenant_id == tenant_id,
                GlobalPayrollConfiguration.country_id == ind_country.id,
            ).first()
            if not ind_cfg:
                ind_cfg = GlobalPayrollConfiguration(
                    tenant_id=tenant_id,
                    legal_entity_id=legal_entity_id,
                    country_id=ind_country.id,
                    default_currency="INR",
                    timezone="Asia/Kolkata",
                    payroll_frequency=PayrollFrequency.MONTHLY.value,
                    payroll_day=28,
                    cutoff_day=20,
                    adapter_code="IN_STATUTORY_ADAPTER",
                    active=True,
                )
                db.add(ind_cfg)
                db.flush()

            ind_pg = db.query(PayrollPayGroup).filter(PayrollPayGroup.tenant_id == tenant_id, PayrollPayGroup.code == "IND-MTH-CORP").first()
            if not ind_pg:
                ind_pg = PayrollPayGroup(
                    tenant_id=tenant_id,
                    payroll_configuration_id=ind_cfg.id,
                    name="India Monthly Corporate Pay Group",
                    code="IND-MTH-CORP",
                    currency="INR",
                    frequency=PayrollFrequency.MONTHLY.value,
                    active=True,
                )
                db.add(ind_pg)
                db.flush()

            # Active Calendar
            from datetime import date
            cal = db.query(PayrollCalendar).filter(PayrollCalendar.tenant_id == tenant_id, PayrollCalendar.pay_group_id == ind_pg.id).first()
            if not cal:
                cal = PayrollCalendar(
                    tenant_id=tenant_id,
                    pay_group_id=ind_pg.id,
                    period_start=date(2026, 9, 1),
                    period_end=date(2026, 9, 30),
                    cutoff_date=date(2026, 9, 20),
                    pay_date=date(2026, 9, 28),
                    status=PayrollCalendarStatus.OPEN.value,
                )
                db.add(cal)

            # Assign demo employee
            if emp_user and emp_user.person_id:
                assign = db.query(EmployeePayrollAssignment).filter(
                    EmployeePayrollAssignment.tenant_id == tenant_id,
                    EmployeePayrollAssignment.person_id == emp_user.person_id,
                ).first()
                if not assign:
                    assign = EmployeePayrollAssignment(
                        tenant_id=tenant_id,
                        person_id=emp_user.person_id,
                        legal_entity_id=legal_entity_id,
                        country_code="IND",
                        pay_group_id=ind_pg.id,
                        currency="INR",
                        effective_from=date(2026, 1, 1),
                        payroll_status=AssignmentPayrollStatus.ACTIVE.value,
                    )
                    db.add(assign)

        db.commit()
        print(f"Seeded {len(DEMO_USERS)} demo users, integrations catalog, Module 15 governance policies, Module 16 finance defaults, Module 17 workforce models, Module 18 learning catalog, Module 19 engagement platform, Module 20 knowledge/communications, and Module 21 global payroll.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
