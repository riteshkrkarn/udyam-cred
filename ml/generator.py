"""
Synthetic data generator for UdyamCred.

Generates realistic shop financial data with hidden health scores,
reconciliation signals, and injected anomalies with ground truth labels.

Architecture:
1. Hidden health score per shop (latent factor)
2. Monthly cash flow based on health and seasonality
3. Derived fields: purchases, stock, GST, deposits
4. Injected anomalies: round-trips, sales inflation, vintage disagreements
5. Labels: default probability and safe EMI
6. Phase 1-2: Tier assignments, source data (AA, GST, UPI), verified windows, photos

Phase 1-2 Tier System:
- Tier 1: 6-12mo bank data, no GST, no Udyam → amounts ≤50k
- Tier 2: 12+ mo bank + GST → amounts ≤250k
- Tier 3: 24+ mo + Udyam + prior repayment → amounts ≤1M
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import logging
from enum import Enum

from generator_config import GeneratorConfig, get_config


logger = logging.getLogger(__name__)


class Tier(Enum):
    """Product tier based on verified evidence."""
    TIER_1 = 1  # Bank data only, ≤50k
    TIER_2 = 2  # Bank + GST, ≤250k
    TIER_3 = 3  # Bank + GST + Udyam + repayment history, ≤1M


@dataclass
class ShopMetadata:
    """Metadata for a generated shop."""
    shop_id: str
    health_score: float
    hidden_default_probability: float
    safe_emi_true: float
    hidden_health_category: str  # 'excellent', 'good', 'fair', 'poor'
    has_roundtrip: bool
    has_sales_inflation: bool
    has_vintage_disagreement: bool
    has_supplier_mismatch: bool
    # Phase 1-2 fields
    tier: Tier
    verified_months: int  # Months where AA + (GST or UPI) available
    source_agreement_score: float  # 0.6-0.95 correlation between sources
    location_verified: bool
    has_gst: bool
    has_udyam: bool
    has_prior_repayment: bool


class SyntheticDataGenerator:
    """Generate synthetic shop financial data."""
    
    SHOP_TYPES = ['general_store', 'pharmacy', 'electronics', 'apparel', 'hardware']
    SHOP_SIZES = ['micro', 'small', 'medium']
    CITIES = ['bangalore', 'hyderabad', 'delhi', 'mumbai', 'pune', 'chennai', 
              'kolkata', 'ahmedabad', 'lucknow', 'indore']
    
    SUPPLIER_IDS = [f'supplier_{i:04d}' for i in range(100)]
    COUNTERPARTY_IDS = [f'counterparty_{i:04d}' for i in range(200)]
    
    def __init__(self, config: GeneratorConfig):
        """Initialize generator with configuration."""
        self.config = config
        self.rng = np.random.RandomState(config.seed)
        self.shop_metadata: Dict[str, ShopMetadata] = {}
        
    def generate(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, 
                                pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame,
                                pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, ShopMetadata]]:
        """
        Generate all tables including Phase 1-2 tier system.
        
        Returns:
            Tuple of (shops, monthly_flows, purchases, stock_snapshots, 
                     vintage_signals, transfers, labels, tier_assignments,
                     source_data, verified_windows, photos, metadata)
        """
        logger.info(f"Generating dataset with config: generator_id={self.config.generator_id}, "
                   f"n_shops={self.config.n_shops}, seed={self.config.seed}")
        
        # Generate base shops
        shops_df = self._generate_shops()
        
        # Generate monthly cash flows and related data
        monthly_flows_df, purchases_df, stock_snapshots_df, transfers_df = \
            self._generate_monthly_data(shops_df)
        
        # Generate source data (AA, GST, UPI) - Phase 1-2
        source_data_df = self._generate_source_data(shops_df, monthly_flows_df)
        
        # Calculate verified windows (Phase 1-2) - this updates metadata
        verified_windows_df = self._calculate_verified_windows(source_data_df, shops_df)
        
        # Assign tiers with updated metadata (Phase 1-2)
        tier_assignments_df = self._assign_tiers(shops_df)
        
        # Generate photo metadata (Phase 1-2)
        photos_df = self._generate_photos(shops_df)
        
        # Generate vintage signals
        vintage_signals_df = self._generate_vintage_signals(shops_df)
        
        # Generate labels
        labels_df = self._generate_labels(shops_df)
        
        logger.info(f"Generated {len(shops_df)} shops with {len(monthly_flows_df)} monthly rows")
        logger.info(f"Default rate: {labels_df['default_6m'].mean():.2%}")
        logger.info(f"Tier distribution: T1={sum(m.tier == Tier.TIER_1 for m in self.shop_metadata.values())}, "
                   f"T2={sum(m.tier == Tier.TIER_2 for m in self.shop_metadata.values())}, "
                   f"T3={sum(m.tier == Tier.TIER_3 for m in self.shop_metadata.values())}")
        logger.info(f"Anomalies - Roundtrip: {sum(m.has_roundtrip for m in self.shop_metadata.values())}, "
                   f"Sales inflation: {sum(m.has_sales_inflation for m in self.shop_metadata.values())}, "
                   f"Vintage disagreement: {sum(m.has_vintage_disagreement for m in self.shop_metadata.values())}")
        
        return (shops_df, monthly_flows_df, purchases_df, stock_snapshots_df, 
                vintage_signals_df, transfers_df, labels_df, tier_assignments_df,
                source_data_df, verified_windows_df, photos_df, self.shop_metadata)
    
    def _generate_shops(self) -> pd.DataFrame:
        """Generate shop base data."""
        shops = []
        
        for i in range(self.config.n_shops):
            shop_id = f'shop_{self.config.generator_id:02d}_{i:06d}'
            
            # Base attributes
            shop_type = self.rng.choice(self.SHOP_TYPES)
            shop_size = self.rng.choice(self.SHOP_SIZES)
            city = self.rng.choice(self.CITIES)
            rented_or_owned = self.rng.choice(['rented', 'owned'], p=[0.7, 0.3])
            
            # Vintage in months (how long the shop has been running)
            vintage_months = int(self.rng.uniform(6, 120))
            
            # Family size (affects household surplus and EMI cap)
            family_size = int(self.rng.normal(4, 1.5))
            family_size = max(1, min(10, family_size))
            
            # Hidden health score (latent factor driving all else)
            health_score = self.rng.normal(self.config.health_mean, self.config.health_std)
            health_score = np.clip(health_score, 0, 1)
            
            # Categorize health
            if health_score >= 0.75:
                health_category = 'excellent'
            elif health_score >= 0.55:
                health_category = 'good'
            elif health_score >= 0.35:
                health_category = 'fair'
            else:
                health_category = 'poor'
            
            # Default probability rises with poor health and volatility
            default_prob = self.config.default_rate_base * (1 - health_score * 0.8)
            
            # Safe EMI increases with health and decreases with family size
            # Base safe EMI is proportional to health
            base_safe_emi = 5000 + health_score * 15000
            household_factor = 1.0 - (family_size - 2) * 0.05  # More family = less safe EMI
            safe_emi = base_safe_emi * household_factor
            safe_emi = max(2000, safe_emi)
            
            # Optional co-borrower score (not always present)
            co_borrower_score = self.rng.uniform(300, 750) if self.rng.rand() > 0.7 else None
            
            shops.append({
                'shop_id': shop_id,
                'city': city,
                'shop_type': shop_type,
                'shop_size': shop_size,
                'rented_or_owned': rented_or_owned,
                'vintage_months': vintage_months,
                'family_size': family_size,
                'co_borrower_score': co_borrower_score,
                'synthetic': True,
            })
            
            # Phase 1-2: Determine data sources
            # Distribution: 30% Tier 1, 50% Tier 2, 20% Tier 3
            tier_rand = self.rng.rand()
            if tier_rand < 0.30:
                tier = Tier.TIER_1
                has_gst = False
                has_udyam = False
                has_prior_repayment = False
            elif tier_rand < 0.80:
                tier = Tier.TIER_2
                has_gst = True
                has_udyam = False
                has_prior_repayment = False
            else:
                tier = Tier.TIER_3
                has_gst = True
                has_udyam = True
                has_prior_repayment = True
            
            # Store metadata
            self.shop_metadata[shop_id] = ShopMetadata(
                shop_id=shop_id,
                health_score=health_score,
                hidden_default_probability=default_prob,
                safe_emi_true=safe_emi,
                hidden_health_category=health_category,
                has_roundtrip=self.rng.rand() < self.config.roundtrip_rate,
                has_sales_inflation=self.rng.rand() < self.config.sales_inflation_rate,
                has_vintage_disagreement=self.rng.rand() < self.config.vintage_disagreement_rate,
                has_supplier_mismatch=self.rng.rand() < self.config.supplier_mismatch_rate,
                # Phase 1-2
                tier=tier,
                verified_months=0,  # Will be calculated later
                source_agreement_score=0.0,  # Will be calculated later
                location_verified=self.rng.rand() > 0.1,  # 90% have verified location
                has_gst=has_gst,
                has_udyam=has_udyam,
                has_prior_repayment=has_prior_repayment,
            )
        
        return pd.DataFrame(shops)
    
    def _generate_monthly_data(self, shops_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Generate monthly flows, purchases, stock and transfers."""
        monthly_flows_list = []
        purchases_list = []
        stock_snapshots_list = []
        transfers_list = []
        
        for _, shop_row in shops_df.iterrows():
            shop_id = shop_row['shop_id']
            metadata = self.shop_metadata[shop_id]
            
            # Determine history length for this shop
            if self.rng.rand() < self.config.keep_thin_history_rate:
                months = int(self.rng.uniform(6, 12))
            else:
                months = self.config.months_per_shop
            
            # Generate monthly data
            for month_offset in range(months):
                flows, purchases, stock = self._generate_month(
                    shop_id=shop_id,
                    month_offset=month_offset,
                    metadata=metadata,
                    shop_row=shop_row,
                )
                
                monthly_flows_list.append(flows)
                purchases_list.extend(purchases)
                stock_snapshots_list.append(stock)
            
            # Generate transfers (some shops have round-trip anomalies)
            transfers = self._generate_transfers(shop_id, metadata, months)
            transfers_list.extend(transfers)
        
        return (
            pd.DataFrame(monthly_flows_list),
            pd.DataFrame(purchases_list),
            pd.DataFrame(stock_snapshots_list),
            pd.DataFrame(transfers_list),
        )
    
    def _generate_month(self, shop_id: str, month_offset: int, metadata: ShopMetadata,
                       shop_row: pd.Series) -> Tuple[Dict, List[Dict], Dict]:
        """Generate data for one shop-month."""
        
        health = metadata.health_score
        month_date = datetime.now() - timedelta(days=30 * (self.config.months_per_shop - month_offset))
        
        # Seasonality: apply multiplier based on month of year
        month_of_year = month_date.month
        seasonality = self._get_seasonality_factor(month_of_year)
        
        # Base monthly revenue (determined by health and shop size)
        shop_size_multiplier = {'micro': 50000, 'small': 150000, 'medium': 400000}
        base_revenue = shop_size_multiplier[shop_row['shop_size']]
        
        # Revenue = base * health * seasonality + noise
        revenue_trend = 0.98 + (month_offset / self.config.months_per_shop) * 0.04  # Slight uptrend or downtrend
        noise = self.rng.normal(1.0, 0.15)  # Noise in revenue
        monthly_revenue = base_revenue * health * seasonality * revenue_trend * noise
        monthly_revenue = max(10000, monthly_revenue)  # Floor on revenue
        
        # UPI inflow is primary revenue channel
        upi_inflow = monthly_revenue * 0.6
        
        # Cash deposits (informal economy)
        cash_deposits = monthly_revenue * 0.25
        
        # Cash withdrawals (owner drawings + expenses)
        owner_draw_rate = 0.3 + (1 - health) * 0.2
        cash_withdrawals = monthly_revenue * owner_draw_rate
        
        # GST turnover (for MSME, typically similar to sales)
        gst_turnover = monthly_revenue * 0.95
        gst_filed = 1 if self.rng.rand() > 0.05 else 0  # 95% file on time
        
        # Sales value (often close to GST turnover)
        sales_value = gst_turnover * 1.05
        
        # Inject sales inflation for some shops
        if metadata.has_sales_inflation:
            sales_value = sales_value * self.rng.uniform(1.2, 1.5)
        
        # Purchases: typically 60-70% of sales
        purchases_value = sales_value * self.rng.uniform(0.6, 0.75)
        
        # Month-end balance
        month_end_balance = (upi_inflow + cash_deposits - cash_withdrawals - purchases_value * 0.5)
        month_end_balance = max(5000, month_end_balance)
        
        # Expired stock value (waste, shrinkage)
        expired_stock_value = purchases_value * self.rng.uniform(0.02, 0.08)
        
        # Generate individual purchases in this month
        n_purchase_bills = int(self.rng.poisson(5))
        purchases = []
        for bill_num in range(n_purchase_bills):
            bill_amount = self.rng.exponential(purchases_value / n_purchase_bills) if n_purchase_bills > 0 else 0
            supplier_id = self.rng.choice(self.SUPPLIER_IDS)
            supplier_credit_days = int(self.rng.choice([0, 15, 30, 45, 60]))
            
            # Inject supplier mismatch for some shops
            supplier_confirmed = 1 if self.rng.rand() > (
                0.15 if metadata.has_supplier_mismatch else 0.05
            ) else 0
            
            purchases.append({
                'shop_id': shop_id,
                'month': month_date.strftime('%Y-%m'),
                'supplier_id': supplier_id,
                'bill_amount': bill_amount,
                'supplier_credit_days': supplier_credit_days,
                'supplier_confirmed': supplier_confirmed,
            })
        
        # Generate stock snapshot
        # Stock is roughly 2-4 months of purchases (inventory turnover)
        inventory_turnover_days = self.rng.uniform(45, 90)
        stock_value = (purchases_value / 30) * inventory_turnover_days
        
        # Stock composition
        fast_moving_share = self.rng.uniform(0.4, 0.7)
        slow_moving_share = 1 - fast_moving_share
        turnover_days = inventory_turnover_days
        
        stock_snapshot = {
            'shop_id': shop_id,
            'month': month_date.strftime('%Y-%m'),
            'stock_value': stock_value,
            'fast_moving_share': fast_moving_share,
            'slow_moving_share': slow_moving_share,
            'turnover_days': turnover_days,
        }
        
        # Monthly flows
        monthly_flow = {
            'shop_id': shop_id,
            'month': month_date.strftime('%Y-%m'),
            'upi_inflow': upi_inflow,
            'cash_deposits': cash_deposits,
            'cash_withdrawals': cash_withdrawals,
            'gst_turnover': gst_turnover,
            'sales_value': sales_value,
            'purchases_value': purchases_value,
            'month_end_balance': month_end_balance,
            'expired_stock_value': expired_stock_value,
            'gst_filed': gst_filed,
        }
        
        return monthly_flow, purchases, stock_snapshot
    
    def _get_seasonality_factor(self, month: int) -> float:
        """Get seasonality multiplier for month (1-12)."""
        peak_multiplier = 1.0 + self.config.seasonality_amplitude / 2
        trough_multiplier = 1.0 - self.config.seasonality_amplitude / 2
        
        if month in self.config.seasonality_peak_months:
            return peak_multiplier
        elif month in [6, 7, 8]:  # Monsoon typically slow
            return trough_multiplier
        else:
            return 1.0
    
    def _generate_transfers(self, shop_id: str, metadata: ShopMetadata, months: int) -> List[Dict]:
        """Generate transfer records (some with round-trip anomalies)."""
        transfers = []
        
        if metadata.has_roundtrip:
            # Inject round-trip transfer pattern (A -> B -> A)
            round_trip_months = self.rng.choice(range(months), size=2, replace=False)
            
            for month_offset in round_trip_months:
                month_date = datetime.now() - timedelta(days=int(30 * (self.config.months_per_shop - month_offset)))
                amount = self.rng.uniform(50000, 200000)
                
                # First leg: A to B
                counterparty_b = self.rng.choice(self.COUNTERPARTY_IDS)
                transfers.append({
                    'shop_id': shop_id,
                    'counterparty_id': counterparty_b,
                    'month': month_date.strftime('%Y-%m'),
                    'amount': amount,
                    'is_round_trip': 1,
                })
                
                # Second leg: B to A (back)
                transfers.append({
                    'shop_id': shop_id,
                    'counterparty_id': counterparty_b,
                    'month': month_date.strftime('%Y-%m'),
                    'amount': amount * 0.95,  # Slight loss in round trip
                    'is_round_trip': 1,
                })
        else:
            # Normal transfers (mostly to suppliers)
            n_transfers = int(self.rng.poisson(3))
            for _ in range(n_transfers):
                month_offset = int(self.rng.uniform(0, months))
                month_date = datetime.now() - timedelta(days=int(30 * (self.config.months_per_shop - month_offset)))
                amount = self.rng.exponential(50000)
                counterparty_id = self.rng.choice(self.COUNTERPARTY_IDS)
                
                transfers.append({
                    'shop_id': shop_id,
                    'counterparty_id': counterparty_id,
                    'month': month_date.strftime('%Y-%m'),
                    'amount': amount,
                    'is_round_trip': 0,
                })
        
        return transfers
    
    def _assign_tiers(self, shops_df: pd.DataFrame) -> pd.DataFrame:
        """Assign tiers based on metadata."""
        tier_assignments = []
        
        for shop_id, metadata in self.shop_metadata.items():
            tier_assignments.append({
                'shop_id': shop_id,
                'tier': metadata.tier.value,
                'has_gst': metadata.has_gst,
                'has_udyam': metadata.has_udyam,
                'has_prior_repayment': metadata.has_prior_repayment,
                'verified_months': metadata.verified_months,
                'source_agreement_score': metadata.source_agreement_score,
            })
        
        return pd.DataFrame(tier_assignments)
    
    def _generate_source_data(self, shops_df: pd.DataFrame, monthly_flows_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate source data (AA, GST, UPI flows) with realistic overlaps.
        
        - Tier 1: AA + UPI for 6-12 months, no GST
        - Tier 2: AA + GST + UPI for 12-24 months
        - Tier 3: AA + GST + UPI for 24+ months
        """
        source_data_list = []
        
        for _, flow_row in monthly_flows_df.iterrows():
            shop_id = flow_row['shop_id']
            metadata = self.shop_metadata[shop_id]
            month = flow_row['month']
            
            # Parse month to get ordinal position
            month_date = pd.to_datetime(month)
            
            # Determine data availability based on tier and hidden health
            # Healthier shops have more complete data
            health = metadata.health_score
            data_completeness = 0.85 + health * 0.15
            
            # AA (bank) flow - always available if shop started banking
            aa_flow = flow_row['upi_inflow'] if self.rng.rand() < data_completeness else None
            
            # GST flow - only for Tier 2 and 3
            if metadata.has_gst and self.rng.rand() < data_completeness:
                gst_flow = flow_row['gst_turnover']
            else:
                gst_flow = None
            
            # UPI flow - always available for shops with UPI
            upi_flow = flow_row['upi_inflow'] if self.rng.rand() < (0.95 + health * 0.05) else None
            
            source_data_list.append({
                'shop_id': shop_id,
                'month': month,
                'aa_flow': aa_flow,
                'gst_flow': gst_flow,
                'upi_flow': upi_flow,
                'tier': metadata.tier.value,
            })
        
        return pd.DataFrame(source_data_list)
    
    def _calculate_verified_windows(self, source_data_df: pd.DataFrame, shops_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate verified windows (months where AA + (GST or UPI) available).
        Also calculate source agreement scores and enforce tier constraints.
        
        Verified window = months where:
        - AA is available AND
        - (GST is available OR UPI is available)
        
        Tier constraints:
        - Tier 1: 6-12 verified months (bank data only)
        - Tier 2: 12-24 verified months (bank + GST)
        - Tier 3: 24+ verified months (bank + GST + Udyam)
        """
        verified_windows_list = []
        
        for shop_id in source_data_df['shop_id'].unique():
            shop_source = source_data_df[source_data_df['shop_id'] == shop_id].copy()
            metadata = self.shop_metadata[shop_id]
            
            # Count verified months (AA + (GST or UPI))
            shop_source['has_aa'] = shop_source['aa_flow'].notna()
            shop_source['has_gst'] = shop_source['gst_flow'].notna()
            shop_source['has_upi'] = shop_source['upi_flow'].notna()
            shop_source['verified'] = (
                shop_source['has_aa'] & (shop_source['has_gst'] | shop_source['has_upi'])
            )
            
            verified_months = shop_source['verified'].sum()
            
            # Enforce tier constraints: reassign tier based on verified_months
            if verified_months < 6:
                # Too little data - force to Tier 1 minimum by padding
                verified_months = self.rng.randint(6, 13)
                tier = Tier.TIER_1
            elif verified_months <= 12:
                tier = Tier.TIER_1
            elif verified_months <= 24:
                tier = Tier.TIER_2
            else:
                tier = Tier.TIER_3
            
            # Update metadata with corrected tier and verified_months
            metadata.tier = tier
            metadata.verified_months = verified_months
            
            # Calculate source agreement score (correlation between overlapping sources)
            # For months where 2+ sources exist, calculate correlation
            overlapping = shop_source[
                (shop_source['has_aa']) & 
                ((shop_source['has_gst']) | (shop_source['has_upi']))
            ]
            
            if len(overlapping) > 0:
                # Normalize flows for comparison
                aa_norm = overlapping['aa_flow'].fillna(0)
                gst_norm = overlapping['gst_flow'].fillna(0)
                upi_norm = overlapping['upi_flow'].fillna(0)
                
                # Calculate pairwise correlations if both sources available
                correlations = []
                
                if (aa_norm > 0).sum() > 0 and (gst_norm > 0).sum() > 0:
                    corr = np.corrcoef(aa_norm + 1, gst_norm + 1)[0, 1]
                    if not np.isnan(corr):
                        correlations.append(corr)
                
                if (aa_norm > 0).sum() > 0 and (upi_norm > 0).sum() > 0:
                    corr = np.corrcoef(aa_norm + 1, upi_norm + 1)[0, 1]
                    if not np.isnan(corr):
                        correlations.append(corr)
                
                if (gst_norm > 0).sum() > 0 and (upi_norm > 0).sum() > 0:
                    corr = np.corrcoef(gst_norm + 1, upi_norm + 1)[0, 1]
                    if not np.isnan(corr):
                        correlations.append(corr)
                
                # Source agreement score = average correlation, normalized to 0.6-0.95 range
                if correlations:
                    avg_corr = np.mean(correlations)
                    # Map from [-1, 1] to [0.6, 0.95]
                    source_agreement = 0.775 + (avg_corr * 0.175)
                else:
                    source_agreement = 0.75
            else:
                source_agreement = 0.6
            
            # Update metadata with source agreement
            metadata.source_agreement_score = np.clip(source_agreement, 0.6, 0.95)
            
            # Calculate window start/end dates
            verified_rows = shop_source[shop_source['verified']]
            if len(verified_rows) > 0:
                window_start = verified_rows.iloc[0]['month']
                window_end = verified_rows.iloc[-1]['month']
            else:
                window_start = None
                window_end = None
            
            verified_windows_list.append({
                'shop_id': shop_id,
                'window_start': window_start,
                'window_end': window_end,
                'months_verified': int(verified_months),
                'agreement_score': metadata.source_agreement_score,
                'tier': metadata.tier.value,
            })
        
        return pd.DataFrame(verified_windows_list)
    
    def _generate_photos(self, shops_df: pd.DataFrame) -> pd.DataFrame:
        """Generate photo metadata with locations and verification status."""
        photos_list = []
        
        PHOTO_TYPES = ['exterior', 'signboard', 'interior', 'shop_front', 'bill_board']
        
        for _, shop_row in shops_df.iterrows():
            shop_id = shop_row['shop_id']
            metadata = self.shop_metadata[shop_id]
            
            # Photos per shop: 3-5
            n_photos = int(self.rng.uniform(3, 6))
            
            for photo_num in range(n_photos):
                # Location: shop_size determines area
                # Use deterministic location based on city + shop_id
                city_lat_map = {
                    'bangalore': 12.97,
                    'hyderabad': 17.37,
                    'delhi': 28.70,
                    'mumbai': 19.08,
                    'pune': 18.52,
                    'chennai': 13.09,
                    'kolkata': 22.57,
                    'ahmedabad': 23.03,
                    'lucknow': 26.85,
                    'indore': 22.72,
                }
                
                base_lat = city_lat_map.get(shop_row['city'], 20.0)
                # Longitude mapping for cities
                city_lng_map = {
                    'bangalore': 77.60,
                    'hyderabad': 78.48,
                    'delhi': 77.20,
                    'mumbai': 72.88,
                    'pune': 73.85,
                    'chennai': 80.28,
                    'kolkata': 88.36,
                    'ahmedabad': 72.58,
                    'lucknow': 80.95,
                    'indore': 75.86,
                }
                base_lng = city_lng_map.get(shop_row['city'], 77.0)
                
                # Add noise for specific shop location
                lat = base_lat + self.rng.uniform(-0.1, 0.1)
                lng = base_lng + self.rng.uniform(-0.1, 0.1)
                
                # Timestamp: random within last 90 days
                days_ago = int(self.rng.uniform(0, 90))
                timestamp = (datetime.now() - timedelta(days=days_ago)).isoformat()
                
                photo_type = self.rng.choice(PHOTO_TYPES)
                verified = 1 if metadata.location_verified and self.rng.rand() > 0.05 else 0
                
                photos_list.append({
                    'shop_id': shop_id,
                    'photo_num': photo_num + 1,
                    'photo_type': photo_type,
                    'location_lat': lat,
                    'location_lng': lng,
                    'timestamp': timestamp,
                    'verified': verified,
                })
        
        return pd.DataFrame(photos_list)
    
    def _generate_vintage_signals(self, shops_df: pd.DataFrame) -> pd.DataFrame:
        """Generate vintage signals (multiple date sources)."""
        vintage_signals = []
        
        for _, shop_row in shops_df.iterrows():
            shop_id = shop_row['shop_id']
            metadata = self.shop_metadata[shop_id]
            vintage_months = shop_row['vintage_months']
            
            # Base date: vintage_months ago
            base_date = datetime.now() - timedelta(days=30 * vintage_months)
            
            # First UPI date (when they first appeared in UPI ecosystem)
            first_upi_date = base_date + timedelta(days=self.rng.randint(0, 30))
            
            # GST registration date (might be before or after UPI)
            gst_registration_date = base_date + timedelta(days=self.rng.randint(-60, 90))
            
            # Udyam registration date (typically after GST)
            udyam_date = gst_registration_date + timedelta(days=self.rng.randint(60, 365))
            
            # First supplier bill date
            first_supplier_bill_date = base_date + timedelta(days=self.rng.randint(-30, 60))
            
            # Lease start date (if rented)
            if shop_row['rented_or_owned'] == 'rented':
                lease_start_date = base_date + timedelta(days=self.rng.randint(-180, 180))
            else:
                lease_start_date = None
            
            # Inject vintage disagreement for some shops
            if metadata.has_vintage_disagreement:
                # Randomly shift one or two dates significantly
                if self.rng.rand() > 0.5:
                    first_upi_date = first_upi_date + timedelta(days=self.rng.randint(-180, 180))
                if self.rng.rand() > 0.5:
                    gst_registration_date = gst_registration_date + timedelta(days=self.rng.randint(-180, 180))
            
            vintage_signals.append({
                'shop_id': shop_id,
                'first_upi_date': first_upi_date.strftime('%Y-%m-%d'),
                'gst_registration_date': gst_registration_date.strftime('%Y-%m-%d'),
                'udyam_date': udyam_date.strftime('%Y-%m-%d'),
                'first_supplier_bill_date': first_supplier_bill_date.strftime('%Y-%m-%d'),
                'lease_start_date': lease_start_date.strftime('%Y-%m-%d') if lease_start_date else None,
            })
        
        return pd.DataFrame(vintage_signals)
    
    def _generate_labels(self, shops_df: pd.DataFrame) -> pd.DataFrame:
        """Generate default labels and safe EMI based on hidden health."""
        labels = []
        
        for shop_id, metadata in self.shop_metadata.items():
            # Default label: based on health, volatility and trends
            # Poor health shops more likely to default
            default_prob = metadata.hidden_default_probability
            
            # Add volatility and trend components
            default_prob = min(0.5, default_prob * self.rng.uniform(0.8, 1.3))
            
            default_6m = 1 if self.rng.rand() < default_prob else 0
            
            labels.append({
                'shop_id': shop_id,
                'default_6m': default_6m,
                'safe_emi_true': metadata.safe_emi_true,
                'hidden_health': metadata.hidden_health_category,
            })
        
        return pd.DataFrame(labels)


def generate_and_save(generator_id: int, output_dir: str = 'ml/data') -> None:
    """Generate dataset and save all tables as CSV."""
    
    config = get_config(generator_id)
    generator = SyntheticDataGenerator(config)
    
    (shops, monthly_flows, purchases, stock_snapshots, vintage_signals, transfers, labels, 
     tier_assignments, source_data, verified_windows, photos, metadata) = generator.generate()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save all tables
    shops.to_csv(output_path / f'shops_gen{generator_id}.csv', index=False)
    monthly_flows.to_csv(output_path / f'monthly_flows_gen{generator_id}.csv', index=False)
    purchases.to_csv(output_path / f'purchases_gen{generator_id}.csv', index=False)
    stock_snapshots.to_csv(output_path / f'stock_snapshots_gen{generator_id}.csv', index=False)
    vintage_signals.to_csv(output_path / f'vintage_signals_gen{generator_id}.csv', index=False)
    transfers.to_csv(output_path / f'transfers_gen{generator_id}.csv', index=False)
    labels.to_csv(output_path / f'labels_gen{generator_id}.csv', index=False)
    
    # Phase 1-2 outputs
    tier_assignments.to_csv(output_path / f'tier_assignments_gen{generator_id}.csv', index=False)
    source_data.to_csv(output_path / f'source_data_gen{generator_id}.csv', index=False)
    verified_windows.to_csv(output_path / f'verified_windows_gen{generator_id}.csv', index=False)
    photos.to_csv(output_path / f'photos_gen{generator_id}.csv', index=False)
    
    # Save config
    config.to_json(output_path / f'config_gen{generator_id}.json')
    
    logger.info(f"Saved all tables to {output_dir}")
    
    # Print sanity checks
    print("\n=== SANITY CHECKS ===")
    print(f"Generator: {generator_id}")
    print(f"Shops: {len(shops)}")
    print(f"Monthly rows: {len(monthly_flows)}")
    print(f"Purchases: {len(purchases)}")
    print(f"Transfers: {len(transfers)}")
    print(f"\nDefault rate: {labels['default_6m'].mean():.2%}")
    print(f"Thin-history shops: {(monthly_flows.groupby('shop_id').size() < 12).sum()}")
    
    # Phase 1-2 stats
    print(f"\n=== PHASE 1-2 STATS ===")
    tier_dist = tier_assignments['tier'].value_counts().sort_index()
    total_shops = len(tier_assignments)
    print(f"Tier distribution:")
    for tier_num in [1, 2, 3]:
        count = tier_dist.get(tier_num, 0)
        pct = (count / total_shops) * 100
        print(f"  Tier {tier_num}: {count} ({pct:.1f}%)")
    
    print(f"\nSource agreement scores:")
    print(f"  Mean: {verified_windows['agreement_score'].mean():.3f}")
    print(f"  Min: {verified_windows['agreement_score'].min():.3f}")
    print(f"  Max: {verified_windows['agreement_score'].max():.3f}")
    
    print(f"\nVerified months:")
    print(f"  Mean: {verified_windows['months_verified'].mean():.1f}")
    print(f"  Median: {verified_windows['months_verified'].median():.1f}")
    
    print(f"\nPhotos:")
    print(f"  Total photos: {len(photos)}")
    print(f"  Verified: {photos['verified'].sum()} ({(photos['verified'].mean() * 100):.1f}%)")
    
    print(f"\nAnomalies:")
    print(f"  Round-trip: {sum(1 for m in metadata.values() if m.has_roundtrip)} shops")
    print(f"  Sales inflation: {sum(1 for m in metadata.values() if m.has_sales_inflation)} shops")
    print(f"  Vintage disagreement: {sum(1 for m in metadata.values() if m.has_vintage_disagreement)} shops")
    print(f"  Supplier mismatch: {sum(1 for m in metadata.values() if m.has_supplier_mismatch)} shops")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Generate both datasets
    print("Generating Generator 1 (training/validation)...")
    generate_and_save(1)
    
    print("\nGenerating Generator 2 (held-out test)...")
    generate_and_save(2)
