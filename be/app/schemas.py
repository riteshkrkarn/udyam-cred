"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, description="User email")
    password: str = Field(..., min_length=8)
    role: str = Field("borrower", description="borrower | officer | approver | auditor")


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="access-token lifetime in seconds")


class UserOut(BaseModel):
    id: int
    email: str
    role: str


class ShopIn(BaseModel):
    """A shop payload submitted for reconciliation."""

    shop_id: int
    gstin: str
    shop_category: str
    purchases: float = Field(..., ge=0)
    gst_turnover: float = Field(..., ge=0)
    upi_turnover: float = Field(..., ge=0)
    inventory_value: float = 0.0
    cash_sales: float = 0.0


class ReconciliationOut(BaseModel):
    shop_id: int | None
    gstin_valid: bool
    shop_category: str
    margin_low: float
    margin_high: float
    goods_sold: float
    expected_sales_low: float
    expected_sales_high: float
    reported_sales: float
    upi_turnover: float
    gst_turnover: float
    verdict: str
    reason: str


class HealthOut(BaseModel):
    status: str
    version: str


# ============================================================================
# Stage 2: Application and Scoring Schemas
# ============================================================================


class EMIScheduleItem(BaseModel):
    """Single month EMI schedule entry."""

    month: int
    principal: float
    interest: float
    balance: float


class FundPlanOut(BaseModel):
    """Recommended fund split across buckets."""

    stock_percent: float
    buffer_percent: float
    expansion_percent: float
    reserve_percent: float
    recommendations: list[str] = []


class ScoringInput(BaseModel):
    """Input for scoring endpoint."""

    application_id: int
    shop_id: int
    family_size: int = Field(..., gt=0)
    monthly_expenses: float = Field(..., gt=0)
    existing_liabilities: float = Field(..., ge=0)
    tenor_months: int = Field(..., gt=0, le=60)


class DecisionOut(BaseModel):
    """Scoring decision output."""

    decision_id: int
    verdict: str  # approved | rejected
    loan_amount: float
    rate_percent: float | None
    emi_monthly: float | None
    emi_schedule: list[EMIScheduleItem] = []
    fund_plan: FundPlanOut | None
    confidence: float
    reasons: list[str]
    abca: float
    household_surplus: float
    safe_amount: float


class ReplayInput(BaseModel):
    """Input for replay endpoint (re-score with overrides)."""

    decision_id: int
    overrides: dict[str, float | int] = {}  # field name -> new value


class OverrideInput(BaseModel):
    """Input for override endpoint."""

    decision_id: int
    new_loan_amount: float = Field(..., gt=0)
    reason: str = Field(..., min_length=10)


class ApplicationCreateInput(BaseModel):
    """Create new application."""

    shop_id: int
    loan_amount_requested: float = Field(..., gt=0)
    purpose: str = Field(..., min_length=5)


class ApplicationOut(BaseModel):
    """Application response."""

    id: int
    borrower_id: int
    shop_id: int
    loan_amount_requested: float
    purpose: str
    status: str
    created_at: str


class ApplicationUpdateInput(BaseModel):
    """Update application status."""

    status: str


class ConsentInput(BaseModel):
    """Create consent."""

    agreed: bool
    consent_text: str = Field(..., min_length=20)


class ConsentOut(BaseModel):
    """Consent response."""

    id: int
    application_id: int
    borrower_agreed: bool
    agreed_at: str | None
    withdrawn_at: str | None


class DocumentOut(BaseModel):
    """Document response."""

    id: int
    application_id: int
    document_type: str
    file_path: str
    uploaded_at: str


class HouseholdDataInput(BaseModel):
    """Create/update household data."""

    family_size: int = Field(..., gt=0)
    dependents: int = Field(..., ge=0)
    monthly_expenses: float = Field(..., gt=0)
    assets: float = Field(..., ge=0)
    liabilities: float = Field(..., ge=0)


class HouseholdDataOut(BaseModel):
    """Household data response."""

    id: int
    application_id: int
    family_size: int
    dependents: int
    monthly_expenses: float
    assets: float
    liabilities: float
    created_at: str


class OverrideOut(BaseModel):
    """Override record response."""

    id: int
    officer_id: int
    old_loan_amount: float
    new_loan_amount: float
    reason: str
    created_at: str


class DecisionAuditOut(BaseModel):
    """Decision with audit trail."""

    decision_id: int
    application_id: int
    verdict: str
    loan_amount: float
    replay_count: int
    overrides: list[OverrideOut]
    created_at: str


# ============================================================================
# Phase 1: Tiered Verification-First System Schemas
# ============================================================================


class TrancheDetailOut(BaseModel):
    """Single tranche details."""

    tranche_num: int
    amount: float
    release_date: str
    tenor_months: int


class Phase1DecisionOut(BaseModel):
    """Phase 1 decision output."""

    decision_id: int
    verdict: str  # approved | rejected
    tier: int | None
    approved_amount: float
    rate_percent: float | None
    tranche_plan: list[TrancheDetailOut] = []
    emi_schedule: list[EMIScheduleItem] = []
    verified_months: int | None
    source_agreement_score: float | None
    location_verified: bool | None
    photo_count: int | None
    reasons: list[str]
    next_tier_criteria: list[str]


class ScoringPhase1Input(BaseModel):
    """Input for Phase 1 scoring endpoint."""

    application_id: int
    consent_given: bool
    family_size: int = Field(..., gt=0)
    monthly_expenses: float = Field(..., gt=0)


class PhotoUploadInput(BaseModel):
    """Upload a photo."""

    photo_type: str  # shop_front | shelves | bills | rent_receipt | udyam | gst
    photo_path: str
    location_lat: float | None = None
    location_lng: float | None = None
    random_code_written: str | None = None


class PhotoOut(BaseModel):
    """Photo response."""

    id: int
    application_id: int
    photo_type: str
    photo_path: str
    location_lat: float | None
    location_lng: float | None
    verification_status: str
    verified_at: str | None


class TrancheListOut(BaseModel):
    """Tranche list response."""

    id: int
    tranche_num: int
    amount: float
    release_date: str
    release_status: str
    emi_count: int
    tenor_months: int


class TrancheDetailsOut(BaseModel):
    """Tranche details with EMI history."""

    id: int
    tranche_num: int
    amount: float
    release_date: str
    release_status: str
    emi_count: int
    tenor_months: int
    repayment_history: list[dict] = []


class RepaymentStatusOut(BaseModel):
    """Repayment status response."""

    tranche_num: int
    emi_num: int
    due_date: str
    amount: float
    paid_date: str | None
    payment_status: str  # pending | ontime | late | missed | bounced
    days_late: int


class NextEMIOut(BaseModel):
    """Next EMI due response."""

    tranche_num: int
    emi_num: int
    due_date: str
    amount: float
    principal: float
    interest: float


class RepaymentMonitorOut(BaseModel):
    """Officer view of all borrowers' EMI status."""

    application_id: int
    borrower_email: str
    tier: int
    total_approved_amount: float
    on_time_count: int
    late_count: int
    missed_count: int
    bounced_count: int
    stop_rule_active: bool
    last_emi_date: str | None
