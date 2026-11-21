"""Fund Split Optimizer - Recommend allocation of loan funds."""
from typing import Any, Optional


def optimize_fund_split(
    loan_amount: float,
    goods_sold: float,
    margin: float,
    category: str,
    monthly_turnover: float,
) -> dict[str, Any]:
    """
    Optimize fund split across stock, buffer, expansion, and reserve.

    Args:
        loan_amount: Approved loan amount
        goods_sold: Estimated goods sold (opening stock + purchases - closing stock)
        margin: Profit margin percentage (0-100)
        category: Shop category (kirana, electronics, etc.)
        monthly_turnover: Average monthly turnover

    Returns:
        {
            stock_pct: float - Percentage for stock (0-100)
            buffer_pct: float - Percentage for buffer cushion
            expansion_pct: float - Percentage for growth/expansion
            reserve_pct: float - Percentage for contingency reserve
            recommendations: list[str] - Text recommendations
        }
    """
    recommendations = []

    # Calculate required stock value
    # Assuming 2-month buffer of goods_sold
    buffer_months = 2
    if margin < 100:
        # margin is on selling price: cost = selling_price / (1 - margin/100)
        # goods_sold is already in cost terms, so stock = goods_sold * buffer_months
        stock_required = goods_sold * buffer_months
    else:
        stock_required = goods_sold * buffer_months

    # Buffer for slow-moving items (20% of stock)
    buffer_amount = stock_required * 0.2

    # Expansion (20% of loan for growth)
    expansion_amount = loan_amount * 0.2

    # Reserve (remainder)
    reserve_amount = max(0.0, loan_amount - stock_required - buffer_amount - expansion_amount)

    # Calculate percentages
    total = max(loan_amount, 1.0)  # Avoid division by zero
    stock_pct = (stock_required / total) * 100.0
    buffer_pct = (buffer_amount / total) * 100.0
    expansion_pct = (expansion_amount / total) * 100.0
    reserve_pct = (reserve_amount / total) * 100.0

    # Cap at 100% (round-off safety)
    total_pct = stock_pct + buffer_pct + expansion_pct + reserve_pct
    if total_pct > 100.0:
        # Scale down proportionally
        scale = 100.0 / total_pct
        stock_pct *= scale
        buffer_pct *= scale
        expansion_pct *= scale
        reserve_pct *= scale

    # Generate recommendations
    if stock_pct < 50:
        recommendations.append(
            f"Stock allocation ({stock_pct:.0f}%) is below typical 50-60%. Consider adjusting margin or turnover."
        )
    elif stock_pct > 75:
        recommendations.append(
            f"Stock allocation ({stock_pct:.0f}%) is high. Ensure turnover can support this inventory."
        )

    if margin < 15:
        recommendations.append(
            "Low margin (< 15%) limits growth potential. Negotiate better terms with suppliers."
        )

    if monthly_turnover > 0 and loan_amount > monthly_turnover * 6:
        recommendations.append(
            "Loan amount is > 6 months of turnover. Ensure growth plans are realistic."
        )

    if reserve_pct < 5:
        recommendations.append(
            "Reserve allocation is low (< 5%). Build contingency for unexpected expenses."
        )

    return {
        "stock_pct": round(stock_pct, 1),
        "buffer_pct": round(buffer_pct, 1),
        "expansion_pct": round(expansion_pct, 1),
        "reserve_pct": round(reserve_pct, 1),
        "recommendations": recommendations,
    }
