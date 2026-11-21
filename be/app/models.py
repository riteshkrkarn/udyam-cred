"""SQLAlchemy ORM models for UdyamCred.

Stage 1 Tables:
  - users: login accounts with a role (borrower, officer, approver, auditor).
  - shops: synthetic shop records (turnover, purchases, GSTIN, category).
  - reconciliation_results: verdict + reconciliation detail per shop.
  - refresh_tokens: hashed, rotating refresh tokens (DB-stored).

Stage 2 Tables:
  - applications: borrower loan applications
  - consent: borrower consent records
  - documents: uploaded documents (bills, purchase orders, etc.)
  - household_data: family budget and liabilities
  - decisions: scoring decisions with loan amount, rate, EMI
  - overrides: officer overrides of decisions
  - audit_logs: audit trail for all entities
  - data_sources: raw data from external adapters (UPI, AA, GST)
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils import utcnow_naive


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="borrower")
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    applications = relationship(
        "Application", back_populates="borrower", cascade="all, delete-orphan"
    )
    overrides = relationship(
        "Override", back_populates="officer", cascade="all, delete-orphan"
    )


class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, unique=True, index=True, nullable=False)
    gstin = Column(String(15), index=True)
    shop_name = Column(String(255))
    shop_category = Column(String(64), nullable=False)
    state_code = Column(String(2))
    gstin_valid = Column(Boolean, default=False, nullable=False)
    upi_turnover = Column(Float, nullable=False, default=0.0)
    gst_turnover = Column(Float, nullable=False, default=0.0)
    purchases = Column(Float, nullable=False, default=0.0)  # cost of goods sold
    inventory_value = Column(Float, nullable=False, default=0.0)
    cash_sales = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    reconciliation_results = relationship(
        "ReconciliationResult", back_populates="shop", cascade="all, delete-orphan"
    )
    applications = relationship(
        "Application", back_populates="shop", cascade="all, delete-orphan"
    )


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    verdict = Column(String(32), nullable=False)  # approved | flagged | rejected
    margin_low = Column(Float)
    margin_high = Column(Float)
    goods_sold = Column(Float)
    expected_sales_low = Column(Float)
    expected_sales_high = Column(Float)
    reported_sales = Column(Float)
    upi_turnover = Column(Float)
    gst_turnover = Column(Float)
    gstin_valid = Column(Boolean)
    reason = Column(Text)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    shop = relationship("Shop", back_populates="reconciliation_results")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    replaced_by = Column(Integer, ForeignKey("refresh_tokens.id"), nullable=True)
    remember_me = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


# ============================================================================
# Stage 2: Application Workflow Tables
# ============================================================================


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    borrower_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    loan_amount_requested = Column(Float, nullable=False)
    purpose = Column(String(255), nullable=True)
    status = Column(
        String(32), nullable=False, default="pending"
    )  # pending | submitted | under_review | approved | rejected
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    borrower = relationship("User", back_populates="applications")
    shop = relationship("Shop", back_populates="applications")
    consents = relationship(
        "Consent", back_populates="application", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="application", cascade="all, delete-orphan"
    )
    household_data = relationship(
        "HouseholdData", back_populates="application", cascade="all, delete-orphan"
    )
    decisions = relationship(
        "Decision", back_populates="application", cascade="all, delete-orphan"
    )
    data_sources = relationship(
        "DataSource", back_populates="application", cascade="all, delete-orphan"
    )
    photos = relationship(
        "Photo", back_populates="application", cascade="all, delete-orphan"
    )
    source_agreement = relationship(
        "SourceAgreement", back_populates="application", cascade="all, delete-orphan", uselist=False
    )
    verified_window = relationship(
        "VerifiedWindow", back_populates="application", cascade="all, delete-orphan", uselist=False
    )
    gst_coverage = relationship(
        "GSTCoverage", back_populates="application", cascade="all, delete-orphan", uselist=False
    )
    tranches = relationship(
        "Tranche", back_populates="application", cascade="all, delete-orphan"
    )
    stop_rule = relationship(
        "StopRule", back_populates="application", cascade="all, delete-orphan", uselist=False
    )
    location_verification = relationship(
        "LocationVerification", back_populates="application", cascade="all, delete-orphan", uselist=False
    )


class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True
    )
    text = Column(Text, nullable=False)
    borrower_agreed = Column(Boolean, nullable=False, default=False)
    agreed_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="consents")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True
    )
    document_type = Column(
        String(32), nullable=False
    )  # bill | purchase | ledger | statement | other
    file_path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="documents")


class HouseholdData(Base):
    __tablename__ = "household_data"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True, unique=True
    )
    family_size = Column(Integer, nullable=False)
    dependents = Column(Integer, nullable=False, default=0)
    monthly_expenses = Column(Float, nullable=False)
    assets = Column(Float, nullable=False, default=0.0)
    liabilities = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="household_data")


class Tier(Base):
    __tablename__ = "tiers"

    id = Column(Integer, primary_key=True)
    tier_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(64), nullable=False)
    min_verified_months = Column(Integer, nullable=False)
    min_amount = Column(Float, nullable=False)
    max_amount = Column(Float, nullable=False)
    rate_adjustment = Column(Float, nullable=False)
    confidence_threshold = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True
    )
    photo_type = Column(
        String(32), nullable=False
    )  # shop_front | shelves | bills | rent_receipt | udyam | gst
    photo_path = Column(String(512), nullable=False)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    random_code_written = Column(String(100), nullable=True)
    verification_status = Column(String(32), default="pending")  # pending | verified | rejected
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="photos")


class SourceAgreement(Base):
    __tablename__ = "source_agreements"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True, unique=True
    )
    upi_monthly_avg = Column(Float, nullable=True)
    aa_monthly_avg = Column(Float, nullable=True)
    gst_monthly_avg = Column(Float, nullable=True)
    agreement_score_percent = Column(Float, nullable=False)
    weighted_sales = Column(Float, nullable=False)
    sources_used = Column(String(100), nullable=False)  # CSV: aa,gst,upi
    confidence = Column(String(32), nullable=False)  # low | medium | high
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="source_agreement")


class VerifiedWindow(Base):
    __tablename__ = "verified_windows"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True, unique=True
    )
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    months_verified = Column(Integer, nullable=False)
    data_quality_score = Column(Float, nullable=False)
    weighted_importance = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="verified_window")


class GSTCoverage(Base):
    __tablename__ = "gst_coverage"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True, unique=True
    )
    purchases_declared = Column(Float, nullable=False)
    gst_turnover = Column(Float, nullable=False)
    coverage_percent = Column(Float, nullable=False)
    reconciliation_flag = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="gst_coverage")


class Tranche(Base):
    __tablename__ = "tranches"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True
    )
    tranche_num = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    release_date = Column(DateTime, nullable=False)
    release_status = Column(
        String(32), nullable=False, default="pending"
    )  # pending | released | repaid
    emi_count = Column(Integer, nullable=False)
    tenor_months = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="tranches")
    repayment_records = relationship(
        "RepaymentRecord", back_populates="tranche", cascade="all, delete-orphan"
    )


class RepaymentRecord(Base):
    __tablename__ = "repayment_records"

    id = Column(Integer, primary_key=True)
    tranche_id = Column(
        Integer, ForeignKey("tranches.id"), nullable=False, index=True
    )
    emi_num = Column(Integer, nullable=False)
    due_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    paid_date = Column(DateTime, nullable=True)
    payment_status = Column(
        String(32), nullable=False, default="pending"
    )  # pending | ontime | late | missed | bounced
    days_late = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    tranche = relationship("Tranche", back_populates="repayment_records")


class StopRule(Base):
    __tablename__ = "stop_rules"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True, unique=True
    )
    missed_emi_count = Column(Integer, nullable=False, default=0)
    frozen_date = Column(DateTime, nullable=True)
    review_required = Column(Boolean, nullable=False, default=False)
    unfrozen_date = Column(DateTime, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="stop_rule")


class LocationVerification(Base):
    __tablename__ = "location_verifications"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True, unique=True
    )
    rent_address = Column(String(512), nullable=True)
    shop_address = Column(String(512), nullable=True)
    photo_location_lat = Column(Float, nullable=True)
    photo_location_lng = Column(Float, nullable=True)
    distance_meters = Column(Float, nullable=True)
    verified_bool = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="location_verification")


class RateEnvironment(Base):
    __tablename__ = "rate_environments"

    id = Column(Integer, primary_key=True)
    rate_date = Column(DateTime, nullable=False, unique=True, index=True)
    tier_1_industry_rate = Column(Float, nullable=False)
    tier_2_industry_rate = Column(Float, nullable=False)
    tier_3_industry_rate = Column(Float, nullable=False)
    source = Column(String(32), nullable=False)  # manual | api
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True
    )
    verdict = Column(String(32), nullable=False)  # approved | rejected
    tier = Column(Integer, nullable=True)
    verified_months = Column(Integer, nullable=True)
    source_agreement_score = Column(Float, nullable=True)
    location_verified = Column(Boolean, nullable=True)
    photo_count = Column(Integer, nullable=True, default=0)
    tranche_plan_json = Column(Text, nullable=True)  # JSON-serialized tranche plan
    reasons_json = Column(Text, nullable=True)  # JSON-serialized list of reasons
    replay_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="decisions")
    overrides = relationship(
        "Override", back_populates="decision", cascade="all, delete-orphan"
    )


class Override(Base):
    __tablename__ = "overrides"

    id = Column(Integer, primary_key=True)
    decision_id = Column(
        Integer, ForeignKey("decisions.id"), nullable=False, index=True
    )
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    old_loan_amount = Column(Float, nullable=False)
    new_loan_amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    decision = relationship("Decision", back_populates="overrides")
    officer = relationship("User", back_populates="overrides")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    entity_type = Column(
        String(32), nullable=False
    )  # application | decision | override
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(32), nullable=False)  # created | updated | overridden
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    details_json = Column(Text, nullable=True)  # JSON for additional context
    timestamp = Column(DateTime, default=utcnow_naive, nullable=False)


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.id"), nullable=False, index=True
    )
    source = Column(String(32), nullable=False)  # upi | aa | gst
    vintage_date = Column(DateTime, nullable=False)
    data_hash = Column(String(64), nullable=True)  # SHA256 hash of data_json
    data_json = Column(Text, nullable=False)  # JSON-serialized data
    fetched_at = Column(DateTime, default=utcnow_naive, nullable=False)

    application = relationship("Application", back_populates="data_sources")
