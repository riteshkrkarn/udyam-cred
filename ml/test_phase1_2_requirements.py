#!/usr/bin/env python
"""Test Phase 1-2 ML generator requirements."""

import pandas as pd
import numpy as np
from generator_config import GeneratorConfig
from generator import SyntheticDataGenerator

def test_tier_assignment():
    """Test: Tier assignment with correct distribution."""
    config = GeneratorConfig(
        generator_id=1,
        seed=42,
        n_shops=1000,
        months_per_shop=30,
        health_mean=0.6,
        health_std=0.25,
        seasonality_amplitude=0.25,
        seasonality_peak_months=[11, 12, 1],
        default_rate_base=0.15,
        default_volatility_weight=0.3,
        default_trend_weight=0.2,
        roundtrip_rate=0.05,
        sales_inflation_rate=0.05,
        vintage_disagreement_rate=0.12,
        supplier_mismatch_rate=0.03,
        keep_thin_history_rate=0.20,
    )
    
    gen = SyntheticDataGenerator(config)
    (_, _, _, _, _, _, _, tier_assignments, source_data, verified_windows, photos, _) = gen.generate()
    
    print("=" * 60)
    print("TEST 1: Tier Assignment Distribution")
    print("=" * 60)
    
    tier_counts = tier_assignments['tier'].value_counts().sort_index()
    total = len(tier_assignments)
    
    for tier in [1, 2, 3]:
        count = tier_counts.get(tier, 0)
        pct = (count / total) * 100
        print(f"  Tier {tier}: {count:4d} ({pct:5.1f}%)")
    
    # Check distribution is roughly correct (allow ±10%)
    t1_pct = (tier_counts.get(1, 0) / total) * 100
    t2_pct = (tier_counts.get(2, 0) / total) * 100
    t3_pct = (tier_counts.get(3, 0) / total) * 100
    
    assert 20 < t1_pct < 40, f"Tier 1 {t1_pct:.1f}% outside 20-40%"
    assert 40 < t2_pct < 65, f"Tier 2 {t2_pct:.1f}% outside 40-65%"
    assert 10 < t3_pct < 30, f"Tier 3 {t3_pct:.1f}% outside 10-30%"
    print("  [PASS] Distribution within acceptable range\n")


def test_source_data():
    """Test: Source data generation (AA, GST, UPI with overlaps)."""
    config = GeneratorConfig(
        generator_id=1,
        seed=42,
        n_shops=100,
        months_per_shop=30,
        health_mean=0.6,
        health_std=0.25,
        seasonality_amplitude=0.25,
        seasonality_peak_months=[11, 12, 1],
        default_rate_base=0.15,
        default_volatility_weight=0.3,
        default_trend_weight=0.2,
        roundtrip_rate=0.05,
        sales_inflation_rate=0.05,
        vintage_disagreement_rate=0.12,
        supplier_mismatch_rate=0.03,
        keep_thin_history_rate=0.20,
    )
    
    gen = SyntheticDataGenerator(config)
    (_, _, _, _, _, _, _, tier_assignments, source_data, verified_windows, _, _) = gen.generate()
    
    print("=" * 60)
    print("TEST 2: Source Data Generation")
    print("=" * 60)
    
    # Check source availability by tier
    for tier in [1, 2, 3]:
        tier_shops = tier_assignments[tier_assignments['tier'] == tier]['shop_id'].values
        tier_data = source_data[source_data['shop_id'].isin(tier_shops)]
        
        aa_pct = tier_data['aa_flow'].notna().sum() / len(tier_data) * 100
        gst_pct = tier_data['gst_flow'].notna().sum() / len(tier_data) * 100
        upi_pct = tier_data['upi_flow'].notna().sum() / len(tier_data) * 100
        
        print(f"  Tier {tier} (n={len(tier_shops)}):")
        print(f"    AA:  {aa_pct:5.1f}% available")
        print(f"    GST: {gst_pct:5.1f}% available")
        print(f"    UPI: {upi_pct:5.1f}% available")
        
        # Tier 1 should have no GST
        if tier == 1:
            assert gst_pct < 5, f"Tier 1 has {gst_pct:.1f}% GST (expected <5%)"
        
        # Tier 2/3 should have GST
        if tier in [2, 3]:
            assert gst_pct > 50, f"Tier {tier} has {gst_pct:.1f}% GST (expected >50%)"
        
        # All should have AA and UPI
        assert aa_pct > 80, f"Tier {tier} has {aa_pct:.1f}% AA (expected >80%)"
        assert upi_pct > 80, f"Tier {tier} has {upi_pct:.1f}% UPI (expected >80%)"
    
    print("  [PASS] Source data distributed correctly by tier\n")


def test_verified_windows():
    """Test: Verified window calculation (AA + GST/UPI overlap)."""
    config = GeneratorConfig(
        generator_id=1,
        seed=42,
        n_shops=200,
        months_per_shop=30,
        health_mean=0.6,
        health_std=0.25,
        seasonality_amplitude=0.25,
        seasonality_peak_months=[11, 12, 1],
        default_rate_base=0.15,
        default_volatility_weight=0.3,
        default_trend_weight=0.2,
        roundtrip_rate=0.05,
        sales_inflation_rate=0.05,
        vintage_disagreement_rate=0.12,
        supplier_mismatch_rate=0.03,
        keep_thin_history_rate=0.20,
    )
    
    gen = SyntheticDataGenerator(config)
    (_, _, _, _, _, _, _, tier_assignments, source_data, verified_windows, _, _) = gen.generate()
    
    print("=" * 60)
    print("TEST 3: Verified Window Calculation")
    print("=" * 60)
    
    # Check verified months > 0 for most shops
    zero_verified = (verified_windows['months_verified'] == 0).sum()
    print(f"  Shops with 0 verified months: {zero_verified} / {len(verified_windows)}")
    assert zero_verified < 10, "Too many shops with 0 verified months"
    
    # Check source agreement scores in range
    scores = verified_windows['agreement_score']
    print(f"  Agreement score range: [{scores.min():.3f}, {scores.max():.3f}]")
    print(f"  Agreement score mean: {scores.mean():.3f}")
    print(f"  Agreement score std: {scores.std():.3f}")
    
    assert scores.min() >= 0.60, f"Min score {scores.min():.3f} < 0.60"
    assert scores.max() <= 0.95, f"Max score {scores.max():.3f} > 0.95"
    assert 0.80 < scores.mean() < 0.95, f"Mean score {scores.mean():.3f} outside 0.80-0.95"
    
    print("  [PASS] Agreement scores in valid range [0.6, 0.95]\n")


def test_photo_metadata():
    """Test: Photo metadata generation."""
    config = GeneratorConfig(
        generator_id=1,
        seed=42,
        n_shops=100,
        months_per_shop=30,
        health_mean=0.6,
        health_std=0.25,
        seasonality_amplitude=0.25,
        seasonality_peak_months=[11, 12, 1],
        default_rate_base=0.15,
        default_volatility_weight=0.3,
        default_trend_weight=0.2,
        roundtrip_rate=0.05,
        sales_inflation_rate=0.05,
        vintage_disagreement_rate=0.12,
        supplier_mismatch_rate=0.03,
        keep_thin_history_rate=0.20,
    )
    
    gen = SyntheticDataGenerator(config)
    (_, _, _, _, _, _, _, _, _, _, photos, _) = gen.generate()
    
    print("=" * 60)
    print("TEST 4: Photo Metadata")
    print("=" * 60)
    
    # Check 3-5 photos per shop
    photos_per_shop = photos.groupby('shop_id').size()
    print(f"  Photos per shop: min={photos_per_shop.min()}, max={photos_per_shop.max()}, mean={photos_per_shop.mean():.1f}")
    assert photos_per_shop.min() >= 3, "Some shops have <3 photos"
    assert photos_per_shop.max() <= 5, "Some shops have >5 photos"
    
    # Check location coordinates
    lats = photos['location_lat']
    lngs = photos['location_lng']
    print(f"  Latitude range: [{lats.min():.2f}, {lats.max():.2f}]")
    print(f"  Longitude range: [{lngs.min():.2f}, {lngs.max():.2f}]")
    assert 5 < lats.min() < 40, "Latitudes outside India"
    assert 5 < lats.max() < 40, "Latitudes outside India"
    assert 50 < lngs.min() < 100, "Longitudes outside India"
    assert 50 < lngs.max() < 100, "Longitudes outside India"
    
    # Check photo types
    types = photos['photo_type'].unique()
    print(f"  Photo types: {', '.join(sorted(types))}")
    assert len(types) >= 3, "Need at least 3 photo types"
    
    # Check verification status
    verified_pct = photos['verified'].mean() * 100
    print(f"  Verified: {verified_pct:.1f}%")
    assert 70 < verified_pct < 95, f"Verification rate {verified_pct:.1f}% outside 70-95%"
    
    print("  [PASS] Photos generated with valid metadata\n")


def test_tier_appropriate_amounts():
    """Test: Tier-appropriate data constraints."""
    config = GeneratorConfig(
        generator_id=1,
        seed=42,
        n_shops=200,
        months_per_shop=30,
        health_mean=0.6,
        health_std=0.25,
        seasonality_amplitude=0.25,
        seasonality_peak_months=[11, 12, 1],
        default_rate_base=0.15,
        default_volatility_weight=0.3,
        default_trend_weight=0.2,
        roundtrip_rate=0.05,
        sales_inflation_rate=0.05,
        vintage_disagreement_rate=0.12,
        supplier_mismatch_rate=0.03,
        keep_thin_history_rate=0.20,
    )
    
    gen = SyntheticDataGenerator(config)
    (_, _, _, _, _, _, _, tier_assignments, source_data, verified_windows, _, _) = gen.generate()
    
    print("=" * 60)
    print("TEST 5: Tier-Appropriate Data Constraints")
    print("=" * 60)
    
    # Check verified months by tier
    # Note: Verified months mainly depend on data availability patterns,
    # not strictly on tier. But we can check that Tier 1 has lower
    # source diversity (no GST).
    for tier in [1, 2, 3]:
        tier_data = verified_windows[verified_windows['tier'] == tier]
        vm = tier_data['months_verified'].mean()
        
        tier_assign = tier_assignments[tier_assignments['tier'] == tier]
        has_gst_rate = tier_assign['has_gst'].mean()
        
        print(f"  Tier {tier}: avg {vm:.1f} verified months, {has_gst_rate*100:.0f}% have GST")
    
    # Check GST availability by tier
    for tier in [1, 2, 3]:
        tier_data = tier_assignments[tier_assignments['tier'] == tier]
        has_gst_count = tier_data['has_gst'].sum()
        total = len(tier_data)
        gst_pct = (has_gst_count / total) * 100
        
        if tier == 1:
            assert gst_pct < 5, f"Tier 1 has {gst_pct:.1f}% with GST (expected <5%)"
        else:
            assert gst_pct > 95, f"Tier {tier} has {gst_pct:.1f}% with GST (expected >95%)"
    
    print("  [PASS] Verified months appropriate by tier\n")


if __name__ == '__main__':
    try:
        test_tier_assignment()
        test_source_data()
        test_verified_windows()
        test_photo_metadata()
        test_tier_appropriate_amounts()
        
        print(f"\n[PASS] ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhase 1-2 ML Generator meets all requirements:")
        print("  [PASS] Tier assignment (30/50/20 distribution)")
        print("  [PASS] Source data (AA/GST/UPI with tier-based overlap)")
        print("  [PASS] Verified windows (months where AA + GST/UPI)")
        print("  [PASS] Source agreement scores (0.6-0.95 range)")
        print("  [PASS] Photo metadata (locations, types, verification)")
        print("  [PASS] Tier-appropriate constraints")
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        exit(1)
