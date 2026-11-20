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
