"""SQLAlchemy ORM models for UdyamCred Stage 1.

Tables:
  - users: login accounts with a role (borrower, officer, approver, auditor).
  - shops: synthetic shop records (turnover, purchases, GSTIN, category).
  - reconciliation_results: verdict + reconciliation detail per shop.
  - refresh_tokens: hashed, rotating refresh tokens (DB-stored).
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
