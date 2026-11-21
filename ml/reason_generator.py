"""
Generate plain-language reasons for scoring decisions.

MVP: Template-based reasons
Final: LLM-based (optional)
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class ReasonGenerator:
    """Generate plain-language explanations for scoring decisions."""
    
    # Template library
    TEMPLATES = {
        # Default probability signals
        'low_default_prob': "Lower default risk (P={:.1%}) based on financial stability",
        'high_default_prob': "Higher default risk (P={:.1%}) due to volatility in cash flows",
        'moderate_default_prob': "Moderate default risk (P={:.1%}) - standard for this segment",
        
        # Cash flow signals
        'strong_cash_inflow': "Strong UPI inflow (₹{:,.0f} avg/month) indicates active business",
        'weak_cash_inflow': "Low UPI inflow (₹{:,.0f} avg/month) - limited turnover",
        'volatile_cash_flow': "Volatile cash flows (std ₹{:,.0f}) - inconsistent revenue",
        'stable_cash_flow': "Stable cash flows (std ₹{:,.0f}) - consistent operations",
        'declining_balance': "Declining account balance trend - shop drawing down reserves",
        'growing_balance': "Growing account balance - shop building reserves",
        
        # GST signals
        'good_gst_match': "Sales and GST reconciliation strong (gap {:.1%}) - transparent reporting",
        'poor_gst_match': "Large gap between sales and GST (gap {:.1%}) - possible under-reporting",
        'gst_filing_consistent': "Consistent GST filings ({:.0%} rate) - regular compliance",
        'gst_filing_inconsistent': "Inconsistent GST filings ({:.0%} rate) - compliance issues",
        
        # Stock signals
        'good_stock_coverage': "Stock value (₹{:,.0f}) covers {} months of sales",
        'low_stock_coverage': "Low stock value relative to sales - supply chain risk",
        'high_inventory_turnover': "Fast inventory turnover ({} days) - efficient operations",
        'slow_inventory_turnover': "Slow inventory turnover ({} days) - potential obsolescence",
        
        # Purchase signals
        'diverse_suppliers': "Strong supplier relationship ({} unique suppliers) - supply stability",
        'few_suppliers': "Limited suppliers ({} unique) - concentration risk",
        'high_confirmation_rate': "High supplier confirmation rate ({:.0%}) - transparent billing",
        'low_confirmation_rate': "Lower supplier confirmation rate ({:.0%}) - unverified bills",
        
        # Vintage signals
        'long_operating_history': "Long operating history ({} months, {} sources) - established business",
        'short_operating_history': "Short operating history ({} months) - new or undocumented",
        'vintage_agreement': "Multiple sources agree on vintage dates - consistent history",
        'vintage_disagreement': "Vintage dates disagree by {} days - unclear history",
        
        # Tier-based
        'tier_1_money_side': "Tier 1: Evidence is money-side only (UPI, bank, photos, ledger)",
        'tier_2_gst_history': "Tier 2: GST filings and long bank history provide documented evidence",
        'tier_3_udyam_repayment': "Tier 3: Udyam registration and repayment record enable tranches",
        
        # Amount signals
        'amount_capacity_limited': "Amount capped by capacity model (₹{:,.0f}) - repayment sustainability",
        'amount_tier_limited': "Amount capped by tier limit (₹{:,.0f}) - tier policy",
        'amount_stock_limited': "Amount capped by stock limit (₹{:,.0f}) - collateral available",
        'amount_at_tier_max': "Amount at tier maximum (₹{:,.0f}) - can't go higher",
        
        # Risk band
        'low_risk_band': "Risk band: LOW - Strong indicators across metrics",
        'moderate_risk_band': "Risk band: MODERATE - Mixed signals, standard approval",
        'high_risk_band': "Risk band: HIGH - Multiple risk factors, requires review",
        'needs_review': "Risk band: NEEDS REVIEW - Insufficient evidence or conflicting signals",
        
        # Confidence
        'high_confidence': "High confidence ({:.0%}) - consistent signals across sources",
        'moderate_confidence': "Moderate confidence ({:.0%}) - some variation in signals",
        'low_confidence': "Low confidence ({:.0%}) - limited or conflicting data",
        
        # Anomalies
        'round_trip_detected': "Round-trip transfer pattern detected ({} transfers) - potential fraud",
        'sales_inflation': "Sales reported higher than stock suggests - possible inflation",
        'no_anomalies': "No anomalies detected - standard transaction patterns",
    }
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize reason generator.
        
        Args:
            use_llm: If True, try to use LLM API for reasons (Final stage)
        """
        self.use_llm = use_llm
        if use_llm:
            logger.warning("LLM-based reasons not yet implemented. Using templates.")
    
    def generate_reasons(self, decision: Dict) -> List[str]:
        """
        Generate list of reasons for a scoring decision.
        
        Args:
            decision: ScoringDecision.to_dict() output
            
        Returns:
            List of plain-language reason strings
        """
        reasons = []
        
        # Tier reason
        tier = decision.get('tier', 0)
        if tier == 1:
            reasons.append(self.TEMPLATES['tier_1_money_side'])
        elif tier == 2:
            reasons.append(self.TEMPLATES['tier_2_gst_history'])
        elif tier == 3:
            reasons.append(self.TEMPLATES['tier_3_udyam_repayment'])
        
        # Default probability signal
        default_prob = decision.get('default_probability', 0)
        if default_prob < 0.08:
            reasons.append(
                self.TEMPLATES['low_default_prob'].format(default_prob)
            )
        elif default_prob < 0.20:
            reasons.append(
                self.TEMPLATES['moderate_default_prob'].format(default_prob)
            )
        else:
            reasons.append(
                self.TEMPLATES['high_default_prob'].format(default_prob)
            )
        
        # Risk band
        risk_band = decision.get('risk_band', 'MODERATE')
        if risk_band == 'Low':
            reasons.append(self.TEMPLATES['low_risk_band'])
        elif risk_band == 'Moderate':
            reasons.append(self.TEMPLATES['moderate_risk_band'])
        elif risk_band == 'High':
            reasons.append(self.TEMPLATES['high_risk_band'])
        else:
            reasons.append(self.TEMPLATES['needs_review'])
        
        # Confidence
        confidence = decision.get('scorecard_confidence', 0)
        if confidence >= 0.7:
            reasons.append(
                self.TEMPLATES['high_confidence'].format(confidence * 100)
            )
        elif confidence >= 0.4:
            reasons.append(
                self.TEMPLATES['moderate_confidence'].format(confidence * 100)
            )
        else:
            reasons.append(
                self.TEMPLATES['low_confidence'].format(confidence * 100)
            )
        
        # Amount reasoning
        capacity = decision.get('capacity_amount', 0)
        tier_cap = decision.get('tier_cap', 0)
        stock_limit = decision.get('stock_limit', 0)
        final_amount = decision.get('final_amount', 0)
        
        # What limited the amount?
        limiting_factor = min(
            [capacity, tier_cap, stock_limit],
            key=lambda x: x if x > 0 else float('inf')
        )
        
        if abs(limiting_factor - capacity) < 1:
            reasons.append(
                self.TEMPLATES['amount_capacity_limited'].format(capacity)
            )
        elif abs(limiting_factor - tier_cap) < 1:
            reasons.append(
                self.TEMPLATES['amount_tier_limited'].format(tier_cap)
            )
        elif abs(limiting_factor - stock_limit) < 1:
            reasons.append(
                self.TEMPLATES['amount_stock_limited'].format(stock_limit)
            )
        
        # Tranches
        tranched = decision.get('tranched', False)
        if tranched:
            reasons.append("Amount released in 3 tranches based on EMI performance")
        else:
            reasons.append("Amount released as single disbursement")
        
        return reasons
    
    def generate_for_shop(self, shop_id: str, decision_data: Dict) -> Dict[str, List[str]]:
        """
        Generate all reason categories for a shop.
        
        Args:
            shop_id: Shop identifier
            decision_data: ScoringDecision.to_dict() output
            
        Returns:
            Dict with reason categories
        """
        reasons = self.generate_reasons(decision_data)
        
        return {
            'shop_id': shop_id,
            'summary': reasons[0] if reasons else "Unable to generate reasons",
            'details': reasons,
            'count': len(reasons)
        }


def demo():
    """Demo reason generation."""
    print("\n" + "="*70)
    print("DEMO: REASON GENERATION")
    print("="*70)
    
    generator = ReasonGenerator()
    
    # Example decision (Tier 2, moderate risk)
    decision = {
        'shop_id': 'shop_001',
        'tier': 2,
        'tier_name': 'TIER_2',
        'default_probability': 0.12,
        'risk_band': 'Moderate',
        'scorecard_confidence': 0.65,
        'safe_emi': 15000,
        'capacity_amount': 360000,
        'tier_cap': 300000,
        'stock_limit': 150000,
        'final_amount': 150000,
        'tranched': False
    }
    
    reasons = generator.generate_reasons(decision)
    
    print(f"\nShop: {decision['shop_id']}")
    print(f"Tier: {decision['tier_name']}")
    print(f"Final Amount: ₹{decision['final_amount']:,.0f}")
    print(f"\nReasons:")
    for i, reason in enumerate(reasons, 1):
        print(f"{i}. {reason}")
    
    # Example 2: Tier 3 with tranches
    print("\n" + "-"*70)
    
    decision_tier3 = {
        'shop_id': 'shop_002',
        'tier': 3,
        'tier_name': 'TIER_3',
        'default_probability': 0.08,
        'risk_band': 'Low',
        'scorecard_confidence': 0.82,
        'safe_emi': 25000,
        'capacity_amount': 600000,
        'tier_cap': 1000000,
        'stock_limit': 400000,
        'final_amount': 400000,
        'tranched': True
    }
    
    reasons_tier3 = generator.generate_reasons(decision_tier3)
    
    print(f"\nShop: {decision_tier3['shop_id']}")
    print(f"Tier: {decision_tier3['tier_name']}")
    print(f"Final Amount: ₹{decision_tier3['final_amount']:,.0f} (tranched)")
    print(f"\nReasons:")
    for i, reason in enumerate(reasons_tier3, 1):
        print(f"{i}. {reason}")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    demo()
