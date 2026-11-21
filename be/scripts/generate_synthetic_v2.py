#!/usr/bin/env python3
"""Generate synthetic v2 data for UdyamCred tiered lending model.

Creates synthetic shops for Tier 1, 2, and 3 with realistic income patterns and evidence.

Run:
    python scripts/generate_synthetic_v2.py
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Shop
from app.utils import utcnow_naive


def create_tables():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created")


def seed_tier_1_shop(db: Session, shop_id: int) -> Shop:
    """Create a Tier 1 shop: money-side evidence only, no GSTIN or repayment history."""
    shop = Shop(
        shop_id=shop_id,
        shop_name=f"Tier 1 Store {shop_id}",
        shop_category="general_retail",
        state_code="KA",
        gstin_valid=False,
        gstin=None,
        upi_turnover=random.uniform(50000, 200000),  # Monthly UPI ~50-200k
        gst_turnover=0,
        purchases=random.uniform(10000, 50000),
        inventory_value=random.uniform(5000, 25000),
        cash_sales=random.uniform(5000, 20000),
    )
    db.add(shop)
    db.flush()
    print(f"  Tier 1 shop {shop_id}: UPI ₹{shop.upi_turnover:.0f}/mo")
    return shop


def seed_tier_2_shop(db: Session, shop_id: int, with_gst: bool = True) -> Shop:
    """Create a Tier 2 shop: GST registered OR long bank history."""
    if with_gst:
        # GST-registered shop
        gstin = f"29ABC{random.randint(100000, 999999)}Z5"  # Mock GSTIN
        gst_turnover = random.uniform(100000, 400000)  # Monthly GST ~100-400k
    else:
        gstin = None
        gst_turnover = 0
    
    shop = Shop(
        shop_id=shop_id,
        shop_name=f"Tier 2 Store {shop_id}",
        shop_category="general_retail",
        state_code="KA",
        gstin=gstin,
        gstin_valid=True if gstin else False,
        upi_turnover=random.uniform(150000, 400000),
        gst_turnover=gst_turnover,
        purchases=random.uniform(50000, 150000),
        inventory_value=random.uniform(20000, 80000),
        cash_sales=random.uniform(20000, 60000),
    )
    db.add(shop)
    db.flush()
    print(f"  Tier 2 shop {shop_id}: UPI ₹{shop.upi_turnover:.0f}/mo, GST {'✓' if gstin else '✗'}")
    return shop


def seed_tier_3_shop(db: Session, shop_id: int) -> Shop:
    """Create a Tier 3 shop: Udyam + repayment record (simulated)."""
    gstin = f"29XYZ{random.randint(100000, 999999)}Z5"  # Mock GSTIN
    
    shop = Shop(
        shop_id=shop_id,
        shop_name=f"Tier 3 Store {shop_id}",
        shop_category="general_retail",
        state_code="KA",
        gstin=gstin,
        gstin_valid=True,
        upi_turnover=random.uniform(300000, 600000),
        gst_turnover=random.uniform(200000, 500000),
        purchases=random.uniform(100000, 300000),
        inventory_value=random.uniform(50000, 150000),
        cash_sales=random.uniform(50000, 100000),
    )
    db.add(shop)
    db.flush()
    print(f"  Tier 3 shop {shop_id}: UPI ₹{shop.upi_turnover:.0f}/mo, GST ₹{shop.gst_turnover:.0f}/mo, Udyam ✓")
    return shop


def main():
    """Generate synthetic v2 data."""
    print("\n📊 Generating synthetic v2 data for UdyamCred tiered lending...\n")
    
    # Create tables
    create_tables()
    
    # Open session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_count = db.query(Shop).count()
        if existing_count > 0:
            print(f"⚠️  Database already has {existing_count} shops. Skipping generation.\n")
            return
        
        print("Generating shops...\n")
        
        shop_id = 100
        
        # Tier 1 shops (3x)
        print("Tier 1 (money-side evidence only):")
        for i in range(3):
            seed_tier_1_shop(db, shop_id)
            shop_id += 1
        print()
        
        # Tier 2 shops (3x)
        print("Tier 2 (GST or long bank history):")
        for i in range(3):
            seed_tier_2_shop(db, shop_id, with_gst=True)
            shop_id += 1
        print()
        
        # Tier 3 shops (3x)
        print("Tier 3 (Udyam + repayment history):")
        for i in range(3):
            seed_tier_3_shop(db, shop_id)
            shop_id += 1
        print()
        
        db.commit()
        
        print("✓ Synthetic data generated successfully")
        print(f"✓ Total shops: {db.query(Shop).count()}\n")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
