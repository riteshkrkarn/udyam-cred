"""Stock reconciliation: does a shop's declared sales match its purchases + margin?

Inputs (a "shop" - a dict from the synthetic generator, or an ORM Shop object):
  - gstin:           GSTIN string (validated for format + checksum)
  - shop_category:   one of the 8 leaf categories in the policy
  - purchases:       cost of goods sold (the goods the shop bought to sell on)
  - gst_turnover:     sales the shop declared on its GST return
  - upi_turnover:     digital (UPI) payment receipts

Logic:
  The spec's inverse formula (margin on selling price) is:
      expected_sales = goods_sold / (1 + margin)
  For a category range [margin_low, margin_high] the expected sales band is:
      expected_sales_high = goods_sold / (1 + margin_low)   (lower margin -> higher sales)
      expected_sales_low  = goods_sold / (1 + margin_high)  (higher margin -> lower sales)
  A tolerance band (policy.tolerance) is applied on both ends before comparison.

Verdicts:
  - rejected: GSTIN fails format/checksum validation.
  - flagged:  UPI receipts exceed declared GST sales, or declared sales fall outside
             the expected margin band (sales suppression / overstatement).
  - approved: declared sales sit inside the expected margin band.
"""
from __future__ import annotations

from typing import Any

from app.gstin import is_valid_gstin
from app.policy import Policy


def _get(shop: Any, name: str, default: Any = None) -> Any:
    """Read a field from a dict (generator output) or an ORM object."""
    if isinstance(shop, dict):
        return shop.get(name, default)
    return getattr(shop, name, default)


def reconcile(shop: Any, policy: Policy) -> dict:
    """Reconcile one shop against the policy and return a verdict + detail dict."""
    gstin = _get(shop, "gstin")
    gstin_valid = is_valid_gstin(gstin) if gstin else False

    category_key = _get(shop, "shop_category")
    cat = policy.get_category(category_key)
    m_low, m_high = cat.margin_low, cat.margin_high
    tol = policy.tolerance

    goods_sold = float(_get(shop, "purchases", 0.0))
    gst_turnover = float(_get(shop, "gst_turnover", 0.0))
    upi_turnover = float(_get(shop, "upi_turnover", 0.0))

    # Inverse formula: expected_sales = goods_sold / (1 + margin).
    # higher margin -> smaller expected sales, so low uses margin_high and vice versa.
    expected_sales_low = goods_sold / (1.0 + m_high)
    expected_sales_high = goods_sold / (1.0 + m_low)

    band_low = expected_sales_low * (1.0 - tol)
    band_high = expected_sales_high * (1.0 + tol)

    if not gstin_valid:
        verdict = "rejected"
        reason = "invalid GSTIN (format or checksum)"
    elif upi_turnover > gst_turnover * (1.0 + tol):
        verdict = "flagged"
        reason = "UPI turnover exceeds declared GST sales (digital receipts above declared total)"
    elif gst_turnover < band_low:
        verdict = "flagged"
        reason = "declared sales below expected margin band (possible sales suppression)"
    elif gst_turnover > band_high:
        verdict = "flagged"
        reason = "declared sales above expected margin band"
    else:
        verdict = "approved"
        reason = "declared sales consistent with category margin band"

    return {
        "shop_id": _get(shop, "shop_id"),
        "gstin_valid": gstin_valid,
        "shop_category": category_key,
        "margin_low": m_low,
        "margin_high": m_high,
        "goods_sold": round(goods_sold, 2),
        "expected_sales_low": round(expected_sales_low, 2),
        "expected_sales_high": round(expected_sales_high, 2),
        "reported_sales": round(gst_turnover, 2),
        "upi_turnover": round(upi_turnover, 2),
        "gst_turnover": round(gst_turnover, 2),
        "verdict": verdict,
        "reason": reason,
    }


def reconcile_many(shops: list, policy: Policy) -> list[dict]:
    """Reconcile a list of shops, preserving order."""
    return [reconcile(s, policy) for s in shops]
