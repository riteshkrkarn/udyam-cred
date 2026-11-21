"""GST Coverage engine: reconcile purchases to GST turnover."""
from dataclasses import dataclass


@dataclass
class GSTCoverageResult:
    """Result of GST coverage check."""

    coverage_percent: float
    reconciliation_flag: bool
    notes: str


class GSTCoverageEngine:
    """Check alignment between purchases and GST turnover."""

    # Tolerance thresholds
    LOWER_THRESHOLD = 0.8  # If coverage < 0.8, flag (underdeclared)
    UPPER_THRESHOLD = 1.2  # If coverage > 1.2, flag (overstated)

    @staticmethod
    def check_coverage(
        purchases_declared: float, gst_turnover: float
    ) -> GSTCoverageResult:
        """
        Compare purchases from bills to GST turnover.

        Args:
            purchases_declared: Total purchases declared on bills (cost of goods)
            gst_turnover: Total turnover from GST filings (selling price)

        Returns:
            GSTCoverageResult with coverage metrics
        """
        if purchases_declared <= 0 or gst_turnover <= 0:
            return GSTCoverageResult(
                coverage_percent=0.0,
                reconciliation_flag=True,
                notes="Invalid purchases or GST turnover values",
            )

        coverage = gst_turnover / purchases_declared

        # Determine if flag is needed
        reconciliation_flag = False
        notes = ""

        if coverage < GSTCoverageEngine.LOWER_THRESHOLD:
            reconciliation_flag = True
            notes = (
                f"GST turnover ({gst_turnover:.0f}) is significantly lower than purchases "
                f"({purchases_declared:.0f}). Possible underdeclaration or incomplete GST filings."
            )
        elif coverage > GSTCoverageEngine.UPPER_THRESHOLD:
            reconciliation_flag = True
            notes = (
                f"GST turnover ({gst_turnover:.0f}) exceeds purchases ({purchases_declared:.0f}). "
                f"Possible bill inflation or GST overstating."
            )
        else:
            notes = (
                f"GST filing aligns well with purchases. Coverage: {coverage * 100:.1f}%"
            )

        return GSTCoverageResult(
            coverage_percent=coverage,
            reconciliation_flag=reconciliation_flag,
            notes=notes,
        )

    @staticmethod
    def verify_coverage(
        purchases_declared: float, gst_turnover: float
    ) -> GSTCoverageResult:
        """
        Alias for check_coverage. Verify GST coverage.

        Args:
            purchases_declared: Total purchases declared on bills (cost of goods)
            gst_turnover: Total turnover from GST filings (selling price)

        Returns:
            GSTCoverageResult with coverage metrics
        """
        return GSTCoverageEngine.check_coverage(purchases_declared, gst_turnover)
