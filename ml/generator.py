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
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import logging

from generator_config import GeneratorConfig, get_config


logger = logging.getLogger(__name__)


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
                                pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, ShopMetadata]]:
        """
        Generate all tables.
        
        Returns:
            Tuple of (shops, monthly_flows, purchases, stock_snapshots, 
                     vintage_signals, transfers, labels, metadata)
        """
        logger.info(f"Generating dataset with config: generator_id={self.config.generator_id}, "
                   f"n_shops={self.config.n_shops}, seed={self.config.seed}")
        
        # Generate base shops
        shops_df = self._generate_shops()
        
        # Generate monthly cash flows and related data
        monthly_flows_df, purchases_df, stock_snapshots_df, transfers_df = \
            self._generate_monthly_data(shops_df)
        
        # Generate vintage signals
        vintage_signals_df = self._generate_vintage_signals(shops_df)
        
        # Generate labels
        labels_df = self._generate_labels(shops_df)
        
        logger.info(f"Generated {len(shops_df)} shops with {len(monthly_flows_df)} monthly rows")
        logger.info(f"Default rate: {labels_df['default_6m'].mean():.2%}")
        logger.info(f"Anomalies - Roundtrip: {sum(m.has_roundtrip for m in self.shop_metadata.values())}, "
                   f"Sales inflation: {sum(m.has_sales_inflation for m in self.shop_metadata.values())}, "
                   f"Vintage disagreement: {sum(m.has_vintage_disagreement for m in self.shop_metadata.values())}")
        
        return (shops_df, monthly_flows_df, purchases_df, stock_snapshots_df, 
                vintage_signals_df, transfers_df, labels_df, self.shop_metadata)
    
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
    
    shops, monthly_flows, purchases, stock_snapshots, vintage_signals, transfers, labels, metadata = generator.generate()
    
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
    print(f"Anomalies:")
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
