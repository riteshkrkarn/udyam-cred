"""Source Agreement engine: compare sales from multiple sources."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceAgreementResult:
    """Result of source agreement check."""

    weighted_sales: float
    aa_weight: float
    gst_weight: float
    upi_weight: float
    agreement_score: float  # 0-1
    sources_used: list[str]
    confidence: str  # low | medium | high


class SourceAgreementEngine:
    """Compare sales estimates from AA, GST, UPI sources."""

    # Source weights
    AA_WEIGHT = 0.6  # Account Aggregator (most reliable)
    GST_WEIGHT = 0.3  # GST filings
    UPI_WEIGHT = 0.1  # UPI data

    @staticmethod
    def calculate_agreement_score(
        aa_avg: Optional[float],
        gst_avg: Optional[float],
        upi_avg: Optional[float],
    ) -> float:
        """
        Calculate agreement score based on how well sources align.

        Args:
            aa_avg: Average monthly sales from Account Aggregator
            gst_avg: Average monthly sales from GST filings
            upi_avg: Average monthly sales from UPI data

        Returns:
            Agreement score (0-1), where 1 = perfect agreement
        """
        sources = []
        if aa_avg is not None and aa_avg > 0:
            sources.append(aa_avg)
        if gst_avg is not None and gst_avg > 0:
            sources.append(gst_avg)
        if upi_avg is not None and upi_avg > 0:
            sources.append(upi_avg)

        if len(sources) == 0:
            return 0.0
        if len(sources) == 1:
            # Only one source: weak confidence
            return 0.5
        if len(sources) == 2:
            # Two sources: correlation-based
            s1, s2 = sorted(sources)
            if s1 == 0:
                return 0.5
            ratio = s2 / s1
            # If ratio is 1.0-1.2, high agreement; if 1.2-1.5, medium; >1.5 low
            if ratio <= 1.1:
                return 0.95
            elif ratio <= 1.2:
                return 0.85
            elif ratio <= 1.5:
                return 0.65
            else:
                return 0.4
        # Three sources
        all_sources = [s for s in sources if s > 0]
        if not all_sources:
            return 0.0
        avg = sum(all_sources) / len(all_sources)
        # Calculate coefficient of variation
        variance = sum((x - avg) ** 2 for x in all_sources) / len(all_sources)
        std_dev = variance ** 0.5
        cv = std_dev / avg if avg > 0 else 1.0
        # CV < 0.1 = high agreement (0.95), CV < 0.2 = medium (0.85), CV < 0.3 = okay (0.70), else very low (0.3)
        if cv < 0.1:
            return 0.95
        elif cv < 0.2:
            return 0.85
        elif cv < 0.3:
            return 0.70
        else:
            return 0.3

    @staticmethod
    def calculate_weighted_sales(
        aa_avg: Optional[float],
        gst_avg: Optional[float],
        upi_avg: Optional[float],
    ) -> tuple[float, list[str]]:
        """
        Calculate weighted average sales across sources.

        Args:
            aa_avg: Average monthly sales from Account Aggregator
            gst_avg: Average monthly sales from GST filings
            upi_avg: Average monthly sales from UPI data

        Returns:
            Tuple of (weighted_sales, sources_used)
        """
        sources_available = []
        source_values = {}
        
        if aa_avg is not None and aa_avg > 0:
            sources_available.append("aa")
            source_values["aa"] = aa_avg
        if gst_avg is not None and gst_avg > 0:
            sources_available.append("gst")
            source_values["gst"] = gst_avg
        if upi_avg is not None and upi_avg > 0:
            sources_available.append("upi")
            source_values["upi"] = upi_avg
        
        if not sources_available:
            return 0.0, []
        
        # Normalize weights based on available sources
        if len(sources_available) == 1:
            # Only one source: use its value directly
            weighted = source_values[sources_available[0]]
            return weighted, sources_available
        elif len(sources_available) == 2:
            # Two sources: renormalize to 1.0
            if "aa" in sources_available and "gst" in sources_available:
                # AA + GST: 60% AA, 40% GST (renormalized from 60/30)
                weighted = source_values["aa"] * 0.6 + source_values["gst"] * 0.4
            elif "aa" in sources_available and "upi" in sources_available:
                # AA + UPI: 60% AA, 40% UPI (renormalized from 60/10)
                weighted = source_values["aa"] * 0.6 + source_values["upi"] * 0.4
            else:  # GST + UPI
                # GST + UPI: 75% GST, 25% UPI (renormalized from 30/10)
                weighted = source_values["gst"] * 0.75 + source_values["upi"] * 0.25
            return weighted, sources_available
        else:  # All three sources
            # Use original weights: 60% AA, 30% GST, 10% UPI
            weighted = (
                source_values["aa"] * SourceAgreementEngine.AA_WEIGHT
                + source_values["gst"] * SourceAgreementEngine.GST_WEIGHT
                + source_values["upi"] * SourceAgreementEngine.UPI_WEIGHT
            )
            return weighted, sources_available

    @staticmethod
    def get_confidence(agreement_score: float, sources_count: int) -> str:
        """
        Determine confidence level from agreement score and source count.

        Args:
            agreement_score: Score from 0-1
            sources_count: Number of sources used

        Returns:
            Confidence level: "low" | "medium" | "high"
        """
        if sources_count < 2:
            return "low"
        if agreement_score >= 0.85:
            return "high"
        elif agreement_score >= 0.70:
            return "medium"
        else:
            return "low"

    @staticmethod
    def verify_sources(
        aa_monthly_avg: Optional[float] = None,
        gst_monthly_avg: Optional[float] = None,
        upi_monthly_avg: Optional[float] = None,
    ) -> SourceAgreementResult:
        """
        Verify source agreement across AA, GST, and UPI data.

        Args:
            aa_monthly_avg: Average monthly sales from Account Aggregator
            gst_monthly_avg: Average monthly sales from GST filings
            upi_monthly_avg: Average monthly sales from UPI data

        Returns:
            SourceAgreementResult with agreement metrics
        """
        # Calculate weighted sales
        weighted_sales, sources_used = SourceAgreementEngine.calculate_weighted_sales(
            aa_monthly_avg, gst_monthly_avg, upi_monthly_avg
        )

        # Calculate agreement score
        agreement_score = SourceAgreementEngine.calculate_agreement_score(
            aa_monthly_avg, gst_monthly_avg, upi_monthly_avg
        )

        # Determine confidence
        confidence = SourceAgreementEngine.get_confidence(
            agreement_score, len(sources_used)
        )

        return SourceAgreementResult(
            weighted_sales=weighted_sales,
            aa_weight=SourceAgreementEngine.AA_WEIGHT if aa_monthly_avg else 0.0,
            gst_weight=SourceAgreementEngine.GST_WEIGHT if gst_monthly_avg else 0.0,
            upi_weight=SourceAgreementEngine.UPI_WEIGHT if upi_monthly_avg else 0.0,
            agreement_score=agreement_score,
            sources_used=sources_used,
            confidence=confidence,
        )
