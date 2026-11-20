"""
Generator configuration for UdyamCred synthetic data.
Stores generator parameters so datasets can be rebuilt exactly.
"""

from dataclasses import dataclass, asdict
from typing import List
import json
from pathlib import Path


@dataclass
class GeneratorConfig:
    """Configuration for synthetic data generator."""
    
    # Generator identification
    generator_id: int  # 1 or 2
    seed: int
    n_shops: int
    months_per_shop: int  # 24-36
    
    # Health score distribution
    health_mean: float  # Mean of latent health score
    health_std: float   # Std dev
    
    # Seasonality parameters
    seasonality_amplitude: float  # Peak to trough amplitude (0-1)
    seasonality_peak_months: List[int]  # Months with peak revenue (1-12)
    
    # Default rate parameters
    default_rate_base: float  # Base default probability
    default_volatility_weight: float  # How much volatility affects default
    default_trend_weight: float  # How much falling trend affects default
    
    # Anomaly injection rates
    roundtrip_rate: float  # Proportion of shops with round-trip transfers
    sales_inflation_rate: float  # Sales inflated relative to stock
    vintage_disagreement_rate: float  # Disagreement between vintage sources
    supplier_mismatch_rate: float  # Supplier confirmation mismatches
    
    # Historical data retention
    keep_thin_history_rate: float  # Proportion of shops with 6-12 months (rest have full history)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self, path: str) -> None:
        """Save configuration to JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_json(cls, path: str) -> 'GeneratorConfig':
        """Load configuration from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)


# Generator 1: Training and validation dataset
GENERATOR_1_CONFIG = GeneratorConfig(
    generator_id=1,
    seed=42,
    n_shops=5000,
    months_per_shop=30,
    health_mean=0.6,
    health_std=0.25,
    seasonality_amplitude=0.25,
    seasonality_peak_months=[11, 12, 1],  # Diwali season
    default_rate_base=0.15,  # 15% base default rate
    default_volatility_weight=0.3,
    default_trend_weight=0.2,
    roundtrip_rate=0.05,
    sales_inflation_rate=0.05,
    vintage_disagreement_rate=0.12,
    supplier_mismatch_rate=0.03,
    keep_thin_history_rate=0.20,
)

# Generator 2: Held-out test dataset (different parameters and seed)
GENERATOR_2_CONFIG = GeneratorConfig(
    generator_id=2,
    seed=123,
    n_shops=1500,
    months_per_shop=30,
    health_mean=0.55,  # Slightly different distribution
    health_std=0.28,
    seasonality_amplitude=0.30,  # Different seasonality
    seasonality_peak_months=[10, 11, 12, 1],
    default_rate_base=0.12,  # Different default rate
    default_volatility_weight=0.35,
    default_trend_weight=0.25,
    roundtrip_rate=0.04,
    sales_inflation_rate=0.06,
    vintage_disagreement_rate=0.15,
    supplier_mismatch_rate=0.04,
    keep_thin_history_rate=0.18,
)


def get_config(generator_id: int) -> GeneratorConfig:
    """Get configuration by generator ID."""
    if generator_id == 1:
        return GENERATOR_1_CONFIG
    elif generator_id == 2:
        return GENERATOR_2_CONFIG
    else:
        raise ValueError(f"Unknown generator ID: {generator_id}")
