"""Verified Window engine: calculate overlapping data periods."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class VerifiedWindowResult:
    """Result of verified window calculation."""

    window_start: datetime
    window_end: datetime
    months_verified: int
    data_quality_score: float  # 0-1
    weight_factor: float  # For amount scaling


class VerifiedWindowEngine:
    """Calculate verified periods where multiple data sources overlap."""

    MIN_VERIFIED_MONTHS = 6  # Minimum for any loan

    @staticmethod
    def count_months(start_date: datetime, end_date: datetime) -> int:
        """
        Count full months between two dates.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Number of full months
        """
        if start_date > end_date:
            return 0

        months = 0
        current = start_date

        while current <= end_date:
            # Move to next month
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1)
            else:
                next_month = current.replace(month=current.month + 1)

            if next_month <= end_date:
                months += 1
            current = next_month

        return months

    @staticmethod
    def calculate_window_overlap(
        aa_start: Optional[datetime],
        aa_end: Optional[datetime],
        gst_start: Optional[datetime],
        gst_end: Optional[datetime],
        upi_start: Optional[datetime],
        upi_end: Optional[datetime],
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Calculate overlap period where AA and (GST or UPI) both exist.

        Args:
            aa_start, aa_end: Account Aggregator data period
            gst_start, gst_end: GST data period
            upi_start, upi_end: UPI data period

        Returns:
            Tuple of (overlap_start, overlap_end) or (None, None)
        """
        # AA is required
        if aa_start is None or aa_end is None:
            return None, None

        # At least one of GST or UPI must be present
        secondary_sources = []
        if gst_start and gst_end:
            secondary_sources.append((gst_start, gst_end))
        if upi_start and upi_end:
            secondary_sources.append((upi_start, upi_end))

        if not secondary_sources:
            return None, None

        # Find the period where AA overlaps with ANY secondary source
        overlap_start = None
        overlap_end = None

        for sec_start, sec_end in secondary_sources:
            # Overlap with AA
            current_start = max(aa_start, sec_start)
            current_end = min(aa_end, sec_end)

            if current_start <= current_end:
                if overlap_start is None or current_start < overlap_start:
                    overlap_start = current_start
                if overlap_end is None or current_end > overlap_end:
                    overlap_end = current_end

        return overlap_start, overlap_end

    @staticmethod
    def calculate_quality_score(
        months_verified: int, sources_count: int
    ) -> float:
        """
        Calculate data quality score.

        Args:
            months_verified: Number of verified months
            sources_count: Number of data sources (2 or 3)

        Returns:
            Quality score (0-1)
        """
        # More months = higher quality
        # More sources = higher quality
        base_score = min(months_verified / 24.0, 1.0)  # Max at 24 months

        if sources_count >= 3:
            return min(base_score * 1.0, 1.0)
        else:  # 2 sources
            return min(base_score * 0.95, 1.0)

    @staticmethod
    def calculate_verification(
        aa_start: Optional[datetime] = None,
        aa_end: Optional[datetime] = None,
        gst_start: Optional[datetime] = None,
        gst_end: Optional[datetime] = None,
        upi_start: Optional[datetime] = None,
        upi_end: Optional[datetime] = None,
        tier_min_months: int = 6,
    ) -> VerifiedWindowResult:
        """
        Calculate verified window and quality metrics.

        Args:
            aa_start, aa_end: Account Aggregator data period
            gst_start, gst_end: GST data period
            upi_start, upi_end: UPI data period
            tier_min_months: Minimum months required for this tier

        Returns:
            VerifiedWindowResult with window details
        """
        # Calculate overlap period
        window_start, window_end = VerifiedWindowEngine.calculate_window_overlap(
            aa_start, aa_end, gst_start, gst_end, upi_start, upi_end
        )

        if window_start is None or window_end is None:
            # No overlap
            return VerifiedWindowResult(
                window_start=datetime.now(),
                window_end=datetime.now(),
                months_verified=0,
                data_quality_score=0.0,
                weight_factor=0.0,
            )

        # Count verified months
        months_verified = VerifiedWindowEngine.count_months(window_start, window_end)

        # Count sources in overlap
        sources_count = 0
        if aa_start and aa_end and aa_start <= window_end and aa_end >= window_start:
            sources_count += 1
        if gst_start and gst_end and gst_start <= window_end and gst_end >= window_start:
            sources_count += 1
        if upi_start and upi_end and upi_start <= window_end and upi_end >= window_start:
            sources_count += 1

        # Calculate quality score
        quality_score = VerifiedWindowEngine.calculate_quality_score(
            months_verified, sources_count
        )

        # Calculate weight factor for amount scaling
        weight_factor = min(months_verified / tier_min_months, 1.0)

        return VerifiedWindowResult(
            window_start=window_start,
            window_end=window_end,
            months_verified=months_verified,
            data_quality_score=quality_score,
            weight_factor=weight_factor,
        )
