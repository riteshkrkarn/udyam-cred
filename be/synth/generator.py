"""Deterministic synthetic shop data generator based on true_health.

The generator is fully deterministic for a given seed. Each shop has a hidden
true_health value (0 to 1) drawn from a seeded random distribution.

Observable numbers are derived from true_health:
  - Healthy shops (true_health > 0.5): Actual sales approximate goods_sold * (1 - margin)
    with realistic 5-10% noise. UPI inflow is 40-60% of actual sales (realistic digital
    adoption). These shops typically approve reconciliation.
  - Unhealthy shops (true_health <= 0.5): 20-40% of UPI inflow is circular (enters then
    leaves as purchases), creating a round-trip transfer pattern. Stock movements don't
    fully support claimed sales. This creates the reconciliation flag: goods_sold doesn't
    justify declared sales.

The pair case is still enforced: shops 0 and 1 share PAIR_UPI but get different verdicts
based on their derived health/purchases. Each shop gets a distinct GSTIN (different state
code via STATE_CODES rotation). The true_health value is included in shop dict for
debugging/analysis.
"""
from __future__ import annotations

import random
from typing import List

from app.gstin import compute_check_digit, make_valid_gstin
from app.policy import Policy

# Indian state codes 01-38; used to give shops distinct GSTINs.
STATE_CODES = [f"{i:02d}" for i in range(1, 39)]

SHOP_NAME_FIRST = [
    "Sri", "New", "Bharat", "Sai", "Metro", "City", "Royal", "Shanti",
    "Anand", "Mega", "Sree", "Janata",
]
SHOP_NAME_SECOND = [
    "Kirana", "Stores", "Provisions", "Mart", "Bazaar", "Traders",
    "General Store", "Supplies", "Corner Shop", "Enterprises",
]

# Category assignment pattern (repeats every 10 shops to maintain determinism).
CATEGORY_PATTERN = [
    "kirana_without_inventory",
    "loose_goods",
    "packaged_fmcg",
    "branded_staples",
    "beverages_impulse",
    "personal_care",
    "general_merchandise",
    "packaged_fmcg",
    "kirana_with_inventory",
    "loose_goods",
]

# Fixed UPI inflow shared by the pair-case shops (0 and 1), seed-independent.
PAIR_UPI = 400_000.00


class SyntheticDataGenerator:
    """Generate deterministic synthetic shop records based on true_health."""

    def __init__(self, policy: Policy, seed: int = 42):
        self.policy = policy
        self.seed = seed
        self.state_codes = list(STATE_CODES)

    # ----- helpers --------------------------------------------------------

    def _gstin(self, idx: int, valid: bool = True) -> str:
        state = self.state_codes[idx % len(self.state_codes)]
        prefix = f"{state}AAACR5049K1Z"
        if valid:
            return make_valid_gstin(prefix)
        # Corrupt the check digit so the structure is valid but the checksum fails.
        good = compute_check_digit(prefix)
        for cand in "ZYXWVUTSR":
            if cand != good:
                return prefix + cand
        return prefix + ("0" if good != "0" else "1")

    def _name(self, idx: int) -> str:
        return (
            f"{SHOP_NAME_FIRST[idx % len(SHOP_NAME_FIRST)]} "
            f"{SHOP_NAME_SECOND[(idx * 3) % len(SHOP_NAME_SECOND)]}"
        )

    def _build_shop(self, idx: int, true_health: float, category_key: str, rng: random.Random) -> dict:
        """Build a shop derived from its true_health value.
        
        Args:
            idx: Shop index (for GSTIN, name, etc.)
            true_health: Hidden health score (0 to 1). Determines behavior:
                - > 0.5: Healthy shop with realistic sales matching goods_sold * (1 - margin)
                - <= 0.5: Unhealthy shop with round-trip transfers
            category_key: Category key from policy
            rng: Seeded random generator
            
        Returns:
            Shop dict with all derived fields including true_health.
        """
        cat = self.policy.get_category(category_key)
        m_low, m_high = cat.margin_low, cat.margin_high
        m_mid = (m_low + m_high) / 2.0

        # Deterministic base purchases with small seeded jitter.
        base = 1_000_000 + idx * 50_000 + rng.randint(0, 9999)
        purchases = float(base)
        
        # Stock movements: opening_stock + purchases - closing_stock = goods_sold
        # For simplicity, we'll set opening and closing to be minimal variations
        # so that goods_sold ≈ purchases
        opening_stock = round(purchases * rng.uniform(0.02, 0.05), 2)  # Small opening stock
        closing_stock = round(purchases * rng.uniform(0.02, 0.05), 2)   # Small closing stock
        goods_sold = opening_stock + purchases - closing_stock

        gstin = self._gstin(idx, valid=True)
        gstin_valid = True

        # Derive observable numbers from true_health.
        if true_health > 0.5:
            # Healthy shop: actual sales should sit within or near the expected margin band.
            # Choose a margin within the category range based on health score.
            # Higher health -> use lower margin (higher sales); lower health -> use higher margin.
            health_ratio = (true_health - 0.5) * 2.0  # Range [0, 1] for health [0.5, 1.0]
            chosen_margin = m_high - (health_ratio * (m_high - m_low))  # Blend towards lower margin
            
            # Expected sales from that margin
            expected_sales = goods_sold / (1.0 - chosen_margin)
            
            # Add 3-8% realistic noise to match real shop variations.
            noise = rng.uniform(0.03, 0.08)
            actual_sales = expected_sales * (1.0 + (noise if rng.random() > 0.5 else -noise * 0.5))
            gst = round(actual_sales, 2)
            
            # UPI inflow around 40-60% of actual sales (realistic digital adoption).
            upi_ratio = rng.uniform(0.40, 0.60)
            upi = round(actual_sales * upi_ratio, 2)
        else:
            # Unhealthy shop: inject round-trip transfers (circular UPI).
            # Declare sales significantly above what stock supports (suppression pattern).
            base_sales = goods_sold / (1.0 - m_mid)
            # Multiplier for inflated sales (1.25-1.45x what stock justifies)
            inflation = rng.uniform(1.25, 1.45)
            gst = round(base_sales * inflation, 2)
            
            # Generate UPI with circular transfers.
            # 20-40% of UPI inflow is circular (enters then leaves as purchases).
            circular_ratio = rng.uniform(0.20, 0.40)
            base_upi = gst * rng.uniform(0.50, 0.70)
            circular_upi = base_upi * circular_ratio
            upi = round(base_upi + circular_upi, 2)

        cash = round(max(gst - upi, 0.0), 2)
        inventory = round(goods_sold * rng.uniform(0.10, 0.20), 2)

        return {
            "shop_id": idx,
            "gstin": gstin,
            "shop_name": self._name(idx),
            "shop_category": category_key,
            "state_code": gstin[:2],
            "gstin_valid": gstin_valid,
            "upi_turnover": upi,
            "gst_turnover": gst,
            "purchases": purchases,
            "opening_stock": opening_stock,
            "closing_stock": closing_stock,
            "inventory_value": inventory,
            "cash_sales": cash,
            "true_health": round(true_health, 4),
        }

    # ----- public API -----------------------------------------------------

    def generate(self, n_shops: int = 10, seed: int | None = None) -> List[dict]:
        """Return n_shops deterministic shop dicts derived from true_health.
        
        Args:
            n_shops: Number of shops to generate.
            seed: Random seed for reproducibility. Defaults to self.seed (42).
            
        Returns:
            List of shop dicts. Same seed always produces the same output.
            Shops 0 and 1 share PAIR_UPI but have different verdicts based on
            their derived health scores and categories.
        """
        if seed is None:
            seed = self.seed
        rng = random.Random(seed)
        shops: List[dict] = []
        
        for idx in range(n_shops):
            # Generate true_health from distribution (more shops are mid-range).
            # Using beta distribution with alpha=2, beta=2 concentrates around 0.5
            # while allowing range 0-1. Then seed the behavior:
            #   - Indices 0, 3, 5, 7, 9, ... get health > 0.5 (healthy, typically approve)
            #   - Indices 1, 2, 4, 6, 8, ... get health <= 0.5 (unhealthy, typically flag)
            # This maintains the verdict mix from the original scenario design.
            base_health = rng.betavariate(2, 2)  # Concentrated around 0.5
            
            # Deterministic health offset per index: alternating pattern.
            # Shift indices 0, 3, 5, 7, 9 (odd scenario count) upward to >0.5.
            # Indices 1, 2, 4, 6, 8 stay at or below 0.5.
            scenario_idx = idx % 10
            if scenario_idx in [0, 3, 5, 7, 9]:  # Should be healthy/approved
                true_health = 0.5 + (base_health * 0.5)  # Range 0.5-1.0
            else:  # Should be unhealthy/flagged or invalid
                true_health = base_health * 0.5  # Range 0.0-0.5
            
            category_key = CATEGORY_PATTERN[idx % len(CATEGORY_PATTERN)]
            shop = self._build_shop(idx, true_health, category_key, rng)
            shops.append(shop)

        # Pair case: shops 0 and 1 share the same UPI inflow but get different
        # verdicts based on their derived health scores and categories.
        # To ensure verdicts differ:
        # - Recalculate shop 0's sales so it approves with PAIR_UPI
        # - Keep shop 1's sales so it flags with PAIR_UPI
        if len(shops) >= 2:
            # For shop 0 (healthy, typically approved):
            # Ensure declared sales fit within the expected margin band even with low UPI.
            cat0 = self.policy.get_category(shops[0]["shop_category"])
            # Recalculate goods_sold using the actual fields
            opening0 = shops[0]["opening_stock"]
            purchases0 = shops[0]["purchases"]
            closing0 = shops[0]["closing_stock"]
            goods0 = opening0 + purchases0 - closing0
            
            # Target the middle of the margin band
            m_low0, m_high0 = cat0.margin_low, cat0.margin_high
            m_mid0 = (m_low0 + m_high0) / 2.0
            target_sales0 = goods0 / (1.0 - m_mid0)
            # Apply 0.5% tolerance buffer to ensure it stays in band
            shops[0]["gst_turnover"] = round(target_sales0 * 0.998, 2)
            shops[0]["upi_turnover"] = PAIR_UPI
            shops[0]["cash_sales"] = round(max(shops[0]["gst_turnover"] - PAIR_UPI, 0.0), 2)
            
            # For shop 1 (unhealthy, typically flagged):
            # Keep it flagged - it has suppression pattern or too much UPI
            shops[1]["upi_turnover"] = PAIR_UPI
            shops[1]["cash_sales"] = round(max(shops[1]["gst_turnover"] - PAIR_UPI, 0.0), 2)
        
        return shops

    def to_dataframe(self, shops: List[dict]):
        """Convert shop dicts to a pandas DataFrame."""
        import pandas as pd

        return pd.DataFrame(shops)

    def generate_csv(self, path: str, n_shops: int = 10, seed: int | None = None) -> str:
        """Generate shops and write them to a CSV, returning the path."""
        import pandas as pd

        shops = self.generate(n_shops, seed=seed)
        df = pd.DataFrame(shops)
        df.to_csv(path, index=False)
        return path
