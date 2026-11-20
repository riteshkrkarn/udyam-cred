"""
Feature builder for UdyamCred ML pipeline.

Transforms raw shop data into features for scorecard and capacity models.
Handles missing data with flags, reconciliation checks, and vintage signals.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class FeatureBuilder:
    """Build features from raw data as of a point in time."""
    
    def __init__(self, as_of_date: str = None):
        """
        Initialize feature builder.
        
        Args:
            as_of_date: Date string YYYY-MM-DD. If None, uses most recent month in data.
        """
        self.as_of_date = as_of_date
    
    def build_features(self,
                      shops: pd.DataFrame,
                      monthly_flows: pd.DataFrame,
                      purchases: pd.DataFrame,
                      stock_snapshots: pd.DataFrame,
                      vintage_signals: pd.DataFrame,
                      transfers: pd.DataFrame,
                      lookback_months: int = 12) -> pd.DataFrame:
        """
        Build feature matrix for all shops as of as_of_date.
        
        Args:
            shops: Base shop attributes
            monthly_flows: Monthly cash flow data
            purchases: Individual purchase bills
            stock_snapshots: Monthly stock snapshots
            vintage_signals: Vintage dates from multiple sources
            transfers: Transfer records (for round-trip detection)
            lookback_months: How many months to lookback for features
            
        Returns:
            Feature matrix with one row per shop
        """
        
        # Determine as_of_date if not specified
        if self.as_of_date is None:
            as_of_date = monthly_flows['month'].max()
        else:
            as_of_date = self.as_of_date
        
        logger.info(f"Building features as of {as_of_date}, lookback {lookback_months} months")
        
        # Filter to lookback period
        lookback_start = self._subtract_months(as_of_date, lookback_months)
        recent_flows = monthly_flows[
            (monthly_flows['month'] >= lookback_start) &
            (monthly_flows['month'] <= as_of_date)
        ].copy()
        
        recent_purchases = purchases[
            (purchases['month'] >= lookback_start) &
            (purchases['month'] <= as_of_date)
        ].copy()
        
        recent_stock = stock_snapshots[
            (stock_snapshots['month'] >= lookback_start) &
            (stock_snapshots['month'] <= as_of_date)
        ].copy()
        
        recent_transfers = transfers[
            (transfers['month'] >= lookback_start) &
            (transfers['month'] <= as_of_date)
        ].copy()
        
        # Build features
        features = []
        
        for _, shop in shops.iterrows():
            shop_id = shop['shop_id']
            
            # Filter shop data
            shop_flows = recent_flows[recent_flows['shop_id'] == shop_id]
            shop_purchases = recent_purchases[recent_purchases['shop_id'] == shop_id]
            shop_stock = recent_stock[recent_stock['shop_id'] == shop_id]
            shop_transfers = recent_transfers[recent_transfers['shop_id'] == shop_id]
            shop_vintage = vintage_signals[vintage_signals['shop_id'] == shop_id].iloc[0]
            
            # Extract features
            feat = self._extract_features(
                shop=shop,
                shop_flows=shop_flows,
                shop_purchases=shop_purchases,
                shop_stock=shop_stock,
                shop_transfers=shop_transfers,
                shop_vintage=shop_vintage,
                as_of_date=as_of_date,
            )
            
            features.append(feat)
        
        features_df = pd.DataFrame(features)
        logger.info(f"Built features for {len(features_df)} shops")
        
        return features_df
    
    def _extract_features(self,
                         shop: pd.Series,
                         shop_flows: pd.DataFrame,
                         shop_purchases: pd.DataFrame,
                         shop_stock: pd.DataFrame,
                         shop_transfers: pd.DataFrame,
                         shop_vintage: pd.Series,
                         as_of_date: str) -> Dict:
        """Extract features for one shop."""
        
        features = {'shop_id': shop['shop_id']}
        
        # === CASH FLOW FEATURES ===
        if len(shop_flows) == 0:
            # No data for this shop
            features.update(self._missing_flow_features())
            features['n_months_data'] = 0
            features['n_months_data_flag'] = 1
        else:
            features['n_months_data'] = len(shop_flows)
            features['n_months_data_flag'] = 0
            
            features['total_upi_inflow'] = shop_flows['upi_inflow'].sum()
            features['avg_upi_inflow'] = shop_flows['upi_inflow'].mean()
            features['std_upi_inflow'] = shop_flows['upi_inflow'].std()
            features['std_upi_inflow_flag'] = 1 if pd.isna(features['std_upi_inflow']) else 0
            
            features['total_cash_deposits'] = shop_flows['cash_deposits'].sum()
            features['avg_cash_deposits'] = shop_flows['cash_deposits'].mean()
            
            # Cash withdrawal rate (higher = more risk)
            features['avg_cash_withdrawal_rate'] = (
                shop_flows['cash_withdrawals'].sum() / shop_flows['upi_inflow'].sum()
                if shop_flows['upi_inflow'].sum() > 0 else 0
            )
            
            # Latest month balance
            latest_flows = shop_flows.sort_values('month').iloc[-1]
            features['latest_month_end_balance'] = latest_flows['month_end_balance']
            features['latest_month_end_balance_flag'] = 0
            
            # Balance trend (positive = improving)
            if len(shop_flows) >= 2:
                oldest_balance = shop_flows.sort_values('month').iloc[0]['month_end_balance']
                features['balance_trend'] = (
                    latest_flows['month_end_balance'] - oldest_balance
                ) / max(1, oldest_balance)
            else:
                features['balance_trend'] = 0
        
        # === GST FEATURES ===
        features['total_gst_turnover'] = shop_flows['gst_turnover'].sum() if len(shop_flows) > 0 else 0
        features['n_gst_filed'] = shop_flows['gst_filed'].sum() if len(shop_flows) > 0 else 0
        features['gst_filing_rate'] = (
            features['n_gst_filed'] / len(shop_flows)
            if len(shop_flows) > 0 else 0
        )
        features['gst_filing_rate_flag'] = 0 if len(shop_flows) > 0 else 1
        
        # === RECONCILIATION FEATURES ===
        rec_feats = self._reconciliation_features(shop_flows)
        features.update(rec_feats)
        
        # === STOCK FEATURES ===
        if len(shop_stock) == 0:
            features['avg_stock_value'] = 0
            features['avg_stock_value_flag'] = 1
            features['avg_fast_moving_share'] = 0.5
            features['avg_turnover_days'] = 60
        else:
            features['avg_stock_value'] = shop_stock['stock_value'].mean()
            features['avg_stock_value_flag'] = 0
            features['avg_fast_moving_share'] = shop_stock['fast_moving_share'].mean()
            features['avg_turnover_days'] = shop_stock['turnover_days'].mean()
        
        # === PURCHASE FEATURES ===
        if len(shop_purchases) == 0:
            features['n_purchase_bills'] = 0
            features['n_suppliers'] = 0
            features['n_purchase_bills_flag'] = 1
            features['supplier_confirmation_rate'] = 0.5  # Unknown
            features['supplier_confirmation_rate_flag'] = 1
        else:
            features['n_purchase_bills'] = len(shop_purchases)
            features['n_suppliers'] = shop_purchases['supplier_id'].nunique()
            features['n_purchase_bills_flag'] = 0
            features['supplier_confirmation_rate'] = (
                shop_purchases['supplier_confirmed'].mean()
            )
            features['supplier_confirmation_rate_flag'] = 0
        
        # === VINTAGE FEATURES ===
        vintage_feats = self._vintage_features(shop_vintage, as_of_date)
        features.update(vintage_feats)
        
        # === TRANSFER ANOMALY FEATURES ===
        transfer_feats = self._transfer_features(shop_transfers)
        features.update(transfer_feats)
        
        # === SHOP ATTRIBUTES ===
        features['shop_type_' + shop['shop_type']] = 1
        features['shop_size_' + shop['shop_size']] = 1
        features['rented_or_owned_rented'] = 1 if shop['rented_or_owned'] == 'rented' else 0
        features['family_size'] = shop['family_size']
        features['shop_vintage_months'] = shop['vintage_months']
        
        # Co-borrower score
        if pd.notna(shop['co_borrower_score']):
            features['has_co_borrower'] = 1
            features['co_borrower_score'] = shop['co_borrower_score']
        else:
            features['has_co_borrower'] = 0
            features['co_borrower_score'] = 0
        
        return features
    
    def _reconciliation_features(self, shop_flows: pd.DataFrame) -> Dict[str, float]:
        """Build reconciliation features (sales vs stock vs GST)."""
        
        features = {}
        
        if len(shop_flows) == 0:
            features['reconciliation_gap_mean'] = 0
            features['reconciliation_gap_std'] = 0
            features['reconciliation_gap_flag'] = 1
            features['sales_gst_correlation'] = 0
            features['sales_gst_correlation_flag'] = 1
            return features
        
        # Reconciliation gap: |sales - gst_turnover| / sales
        # Healthy shops: gap near zero. Anomalies: gap is large.
        sales = shop_flows['sales_value'].values
        gst = shop_flows['gst_turnover'].values
        
        gaps = np.abs(sales - gst) / np.maximum(sales, 1)
        features['reconciliation_gap_mean'] = gaps.mean()
        features['reconciliation_gap_std'] = gaps.std()
        features['reconciliation_gap_flag'] = 0 if not np.isnan(features['reconciliation_gap_std']) else 1
        
        # Correlation: do sales and GST track together?
        if len(shop_flows) >= 2 and sales.std() > 0 and gst.std() > 0:
            features['sales_gst_correlation'] = np.corrcoef(sales, gst)[0, 1]
            features['sales_gst_correlation_flag'] = 0
        else:
            features['sales_gst_correlation'] = 0.5  # Unknown
            features['sales_gst_correlation_flag'] = 1
        
        return features
    
    def _vintage_features(self, shop_vintage: pd.Series, as_of_date: str) -> Dict[str, float]:
        """Build vintage features (signal agreement and age)."""
        
        features = {}
        
        # Parse vintage dates
        dates = {}
        for col in ['first_upi_date', 'gst_registration_date', 'first_supplier_bill_date']:
            try:
                if pd.notna(shop_vintage[col]):
                    dates[col] = pd.to_datetime(shop_vintage[col])
            except:
                pass
        
        if len(dates) == 0:
            features['n_vintage_sources'] = 0
            features['vintage_disagreement_days'] = 0
            features['vintage_disagreement_flag'] = 1
            features['months_since_first_signal'] = 0
            features['months_since_first_signal_flag'] = 1
            return features
        
        # Number of sources available
        features['n_vintage_sources'] = len(dates)
        
        # Disagreement: max - min date
        if len(dates) >= 2:
            max_date = max(dates.values())
            min_date = min(dates.values())
            features['vintage_disagreement_days'] = (max_date - min_date).days
        else:
            features['vintage_disagreement_days'] = 0
        
        features['vintage_disagreement_flag'] = 0
        
        # Months since earliest signal
        if len(dates) > 0:
            earliest = min(dates.values())
            as_of_dt = pd.to_datetime(as_of_date)
            months_diff = (as_of_dt.year - earliest.year) * 12 + (as_of_dt.month - earliest.month)
            features['months_since_first_signal'] = max(0, months_diff)
            features['months_since_first_signal_flag'] = 0
        else:
            features['months_since_first_signal'] = 0
            features['months_since_first_signal_flag'] = 1
        
        return features
    
    def _transfer_features(self, shop_transfers: pd.DataFrame) -> Dict[str, float]:
        """Build transfer anomaly features."""
        
        features = {}
        
        if len(shop_transfers) == 0:
            features['n_transfers'] = 0
            features['n_round_trip_transfers'] = 0
            features['round_trip_transfer_rate'] = 0
            features['n_transfers_flag'] = 1
            features['round_trip_transfer_rate_flag'] = 1
            return features
        
        features['n_transfers'] = len(shop_transfers)
        features['n_transfers_flag'] = 0
        
        features['n_round_trip_transfers'] = shop_transfers['is_round_trip'].sum()
        features['round_trip_transfer_rate'] = (
            features['n_round_trip_transfers'] / len(shop_transfers)
        )
        features['round_trip_transfer_rate_flag'] = 0
        
        return features
    
    def _missing_flow_features(self) -> Dict[str, float]:
        """Create missing flow features with NaN and flags."""
        
        return {
            'total_upi_inflow': 0,
            'avg_upi_inflow': 0,
            'std_upi_inflow': 0,
            'std_upi_inflow_flag': 1,
            'total_cash_deposits': 0,
            'avg_cash_deposits': 0,
            'avg_cash_withdrawal_rate': 0,
            'latest_month_end_balance': 0,
            'latest_month_end_balance_flag': 1,
            'balance_trend': 0,
            'total_gst_turnover': 0,
            'n_gst_filed': 0,
            'gst_filing_rate': 0,
            'gst_filing_rate_flag': 1,
            'reconciliation_gap_mean': 0,
            'reconciliation_gap_std': 0,
            'reconciliation_gap_flag': 1,
            'sales_gst_correlation': 0,
            'sales_gst_correlation_flag': 1,
        }
    
    @staticmethod
    def _subtract_months(date_str: str, months: int) -> str:
        """Subtract months from date string YYYY-MM."""
        year, month = map(int, date_str.split('-'))
        month -= months
        while month <= 0:
            month += 12
            year -= 1
        return f"{year:04d}-{month:02d}"


def build_feature_matrix(generator_id: int, lookback_months: int = 12, 
                        data_dir: str = 'ml/data') -> pd.DataFrame:
    """
    Load generated data and build feature matrix.
    
    Args:
        generator_id: Which generator's data to use (1 or 2)
        lookback_months: Lookback period for features
        data_dir: Directory containing generated CSVs
        
    Returns:
        Feature matrix DataFrame
    """
    
    # Load data
    shops = pd.read_csv(f'{data_dir}/shops_gen{generator_id}.csv')
    monthly_flows = pd.read_csv(f'{data_dir}/monthly_flows_gen{generator_id}.csv')
    purchases = pd.read_csv(f'{data_dir}/purchases_gen{generator_id}.csv')
    stock_snapshots = pd.read_csv(f'{data_dir}/stock_snapshots_gen{generator_id}.csv')
    vintage_signals = pd.read_csv(f'{data_dir}/vintage_signals_gen{generator_id}.csv')
    transfers = pd.read_csv(f'{data_dir}/transfers_gen{generator_id}.csv')
    
    # Build features
    builder = FeatureBuilder()
    features = builder.build_features(
        shops=shops,
        monthly_flows=monthly_flows,
        purchases=purchases,
        stock_snapshots=stock_snapshots,
        vintage_signals=vintage_signals,
        transfers=transfers,
        lookback_months=lookback_months,
    )
    
    return features


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test feature building
    print("Building features for Generator 1...")
    features_gen1 = build_feature_matrix(1, lookback_months=12)
    print(f"Feature matrix shape: {features_gen1.shape}")
    print(f"Features: {features_gen1.columns.tolist()[:10]}...")
    
    # Save
    features_gen1.to_csv('ml/data/features_gen1.csv', index=False)
    print("Saved features_gen1.csv")
