"""Deterministic synthetic shop data generator.

The generator is fully deterministic for a given seed: it uses a seeded
random.Random for cosmetic/numeric jitter, but every shop's *verdict* is fixed
by construction (the relationship between purchases, declared sales and UPI is
chosen per scenario), so the dataset is stable and the verdicts are meaningful
rather than accidental.

Scenario assignment repeats every 10 shops, so the first ten (the golden set,
seed 42) always match tests/golden_expected.csv. The pair case is enforced
explicitly: shops 0 and 1 share the same UPI inflow but get different verdicts
(approved vs flagged) because their purchases and category margins differ.
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

# (scenario_kind, category_key) repeated every 10 shops.
# Verdicts for the first 10 (seed 42):
#   0 approved  1 flagged  2 rejected  3 approved  4 flagged
#   5 approved  6 flagged  7 approved  8 flagged   9 approved
SCENARIOS = [
    ("approved", "kirana_without_inventory"),
    ("suppression", "loose_goods"),
    ("invalid_gstin", "packaged_fmcg"),
    ("approved", "branded_staples"),
    ("upi_exceeds_gst", "beverages_impulse"),
    ("approved", "personal_care"),
    ("suppression", "general_merchandise"),
    ("approved", "packaged_fmcg"),
    ("suppression", "kirana_with_inventory"),
    ("approved", "loose_goods"),
]

# Fixed UPI inflow shared by the pair-case shops (0 and 1), seed-independent.
PAIR_UPI = 400_000.00


class SyntheticDataGenerator:
    """Generate deterministic synthetic shop records."""

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

    def _build_shop(self, idx: int, kind: str, category_key: str, rng: random.Random) -> dict:
        cat = self.policy.get_category(category_key)
        m_low, m_high = cat.margin_low, cat.margin_high
        m_mid = (m_low + m_high) / 2.0

        # Deterministic base purchases with small seeded jitter.
        base = 1_000_000 + idx * 50_000 + rng.randint(0, 9999)
        goods = float(base)

        gstin_valid = kind != "invalid_gstin"
        gstin = self._gstin(idx, valid=gstin_valid)

        if kind == "approved":
            # Declared sales sit at the expected band midpoint -> approved.
            expected = goods / (1.0 - m_mid)
            gst = round(expected, 2)
            upi = round(gst * 0.5, 2)
        elif kind == "suppression":
            # Declared sales well below the band (and above UPI) -> flagged.
            expected_low = goods / (1.0 - m_high)
            gst = round(expected_low * 0.7, 2)
            upi = round(gst * 0.6, 2)
        elif kind == "upi_exceeds_gst":
            # Digital receipts exceed declared sales -> flagged.
            expected = goods / (1.0 - m_mid)
            gst = round(expected, 2)
            upi = round(gst * 1.6, 2)
        elif kind == "invalid_gstin":
            # Numbers would approve, but the GSTIN is invalid -> rejected.
            expected = goods / (1.0 - m_mid)
            gst = round(expected, 2)
            upi = round(gst * 0.5, 2)
        else:
            expected = goods / (1.0 - m_mid)
            gst = round(expected, 2)
            upi = round(gst * 0.5, 2)

        cash = round(max(gst - upi, 0.0), 2)
        inventory = round(goods * rng.uniform(0.10, 0.20), 2)

        return {
            "shop_id": idx,
            "gstin": gstin,
            "shop_name": self._name(idx),
            "shop_category": category_key,
            "state_code": gstin[:2],
            "gstin_valid": gstin_valid,
            "upi_turnover": upi,
            "gst_turnover": gst,
            "purchases": goods,
            "inventory_value": inventory,
            "cash_sales": cash,
        }

    # ----- public API -----------------------------------------------------

    def generate(self, n_shops: int = 10, seed: int | None = None) -> List[dict]:
        """Return n_shops deterministic shop dicts."""
        if seed is None:
            seed = self.seed
        rng = random.Random(seed)
        shops: List[dict] = []
        for idx in range(n_shops):
            kind, category_key = SCENARIOS[idx % len(SCENARIOS)]
            shops.append(self._build_shop(idx, kind, category_key, rng))

        # Pair case: shops 0 and 1 share the same UPI inflow but differ in
        # purchases/category, so they get different verdicts.
        if len(shops) >= 2:
            shops[0]["upi_turnover"] = PAIR_UPI
            shops[1]["upi_turnover"] = PAIR_UPI
            shops[0]["cash_sales"] = round(max(shops[0]["gst_turnover"] - PAIR_UPI, 0.0), 2)
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
