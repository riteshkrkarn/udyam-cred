"""Loader and accessor for the shop-category margin policy (config/policy.yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "policy.yaml"
)


class PolicyError(Exception):
    """Raised when the policy file is missing or structurally invalid."""


class CategoryPolicy:
    """A single category's margin band (margins are fractions of selling price)."""

    def __init__(self, key: str, label: str, margin_low: float, margin_high: float):
        self.key = key
        self.label = label
        self.margin_low = float(margin_low)
        self.margin_high = float(margin_high)
        if self.margin_low > self.margin_high:
            raise PolicyError(
                f"Category {key!r} has margin_low > margin_high "
                f"({self.margin_low} > {self.margin_high})"
            )

    @property
    def margin_mid(self) -> float:
        return (self.margin_low + self.margin_high) / 2.0

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "margin_low": self.margin_low,
            "margin_high": self.margin_high,
        }


class Policy:
    """Parsed policy: tolerance, leaf shop categories and aggregate bands."""

    def __init__(self, raw: dict):
        if not isinstance(raw, dict) or "shop_categories" not in raw:
            raise PolicyError("Policy file is missing the 'shop_categories' section")
        self.version = raw.get("version")
        self.tolerance = float(raw.get("defaults", {}).get("tolerance", 0.005))

        self.aggregates: Dict[str, CategoryPolicy] = {}
        for key, val in (raw.get("aggregates") or {}).items():
            self.aggregates[key] = CategoryPolicy(
                key, val.get("label", key), val["margin_low"], val["margin_high"]
            )

        self.shop_categories: Dict[str, CategoryPolicy] = {}
        for key, val in raw["shop_categories"].items():
            self.shop_categories[key] = CategoryPolicy(
                key, val.get("label", key), val["margin_low"], val["margin_high"]
            )

        if not self.shop_categories:
            raise PolicyError("Policy defines no shop categories")

    def get_category(self, key: str) -> CategoryPolicy:
        if key not in self.shop_categories:
            raise PolicyError(f"Unknown shop category: {key!r}")
        return self.shop_categories[key]

    def leaf_category_keys(self) -> List[str]:
        return list(self.shop_categories.keys())

    def leaf_categories(self) -> List[CategoryPolicy]:
        return list(self.shop_categories.values())


def load_policy(path: str | Path | None = None) -> Policy:
    """Load and validate the policy YAML, returning a Policy object."""
    p = Path(path) if path else DEFAULT_POLICY_PATH
    if not p.exists():
        raise PolicyError(f"Policy file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Policy(raw)
