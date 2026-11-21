"""Plain language reason generation for borrower-facing messages.

This module provides human-readable explanations for:
- Tier assignments (why you got Tier 1/2/3)
- Source verification (where sales data comes from and how well they agree)
- Verification checks (photos, documents, location)
- Next tier criteria (what's needed to unlock the next tier)

All output is in simple English, without jargon.
"""

# ============================================================================
# TIER ASSIGNMENT REASONS
# ============================================================================
# Map tier assignment reason codes to plain English explanations
TIER_REASONS = {
    "verified_6mo": "Verified 6 months of bank data (required for this tier)",
    "verified_12mo": "Verified 12 months of bank data (strong history)",
    "verified_24mo": "Verified 24 months of bank data (excellent history)",
    "no_gst": "Shop not registered for GST (Tier 1 requirement)",
    "gst_registered": "Shop registered for GST (eligible for higher tier)",
    "gst_with_data": "GST filings match bank records",
    "udyam_registered": "Udyam (small business) certificate registered",
    "udyam_required_t3": "Udyam registration required for Tier 3",
    "repayment_history": "Prior repayment record with us - on-time payments",
    "no_repayment_history": "No prior repayment history yet",
    "sales_agreement_high": "Bank and shop sales records agree well",
    "sales_agreement_medium": "Bank and shop sales records mostly agree",
    "sales_agreement_low": "Bank and shop sales records disagree - need more consistent records",
    "photo_verified": "Shop location verified with rent agreement",
    "photo_unverified": "Shop location could not be verified from photos",
    "tier_1_emerging": "Tier 1: Quick loan for emerging businesses",
    "tier_2_registered": "Tier 2: Registered business with GST compliance",
    "tier_3_established": "Tier 3: Established business with verified track record",
}

# ============================================================================
# NEXT TIER CRITERIA
# ============================================================================
# What's needed to reach the next tier
NEXT_TIER_REASONS = {
    "t1_to_t2_months": "Accumulate 12+ months of verified bank data",
    "t1_to_t2_gst": "Register for GST (free, 10-minute online process at gst.gov.in)",
    "t1_to_t2_consistency": "Ensure bank and shop sales records are consistent (within 20%)",
    "t2_to_t3_udyam": "Register for Udyam (free certificate for businesses under 10 crore turnover)",
    "t2_to_t3_months": "Build 24+ months of verified bank data",
    "t2_to_t3_repayment": "Maintain 6+ months of on-time EMI payments",
    "t3_maintain": "Keep repayment on schedule to unlock next tranche",
    "general_consistency": "Keep sales records consistent between sources",
    "general_documentation": "Keep documents (bills, receipts) up to date",
}

# ============================================================================
# SOURCE VERIFICATION REASONS
# ============================================================================
# Explanation of where sales data comes from and how sources agree
SOURCE_REASONS = {
    "aa_only": "Bank data from your official bank account",
    "gst_only": "Sales data from your GST filings with the government",
    "upi_only": "Sales data from UPI transactions",
    "aa_gst_agreement_high": "Your bank and GST records agree {score:.0f}% (excellent match)",
    "aa_gst_agreement_medium": "Your bank and GST records agree {score:.0f}% (good match)",
    "aa_gst_agreement_low": "Your bank and GST records agree only {score:.0f}% (need more consistency)",
    "aa_upi_agreement": "Your bank account and UPI records agree {score:.0f}%",
    "all_sources_agree": "All three sources (bank, GST, UPI) agree on sales figures",
    "single_source": "Only one data source available (weaker evidence)",
    "two_sources": "Two data sources available (good evidence)",
    "three_sources": "Three data sources available (strongest evidence)",
    "insufficient_data": "Not enough data sources to verify sales",
}

# ============================================================================
# VERIFICATION CHECK REASONS
# ============================================================================
# Photo and document verification results
VERIFICATION_REASONS = {
    "photo_shop_verified": "Shop location verified with geo-tagged photo and rent agreement",
    "photo_bills_verified": "Bills or receipts photo verified and visible",
    "photo_udyam_verified": "Udyam certificate verified from photo",
    "photo_gst_verified": "GST filing verified from document photo",
    "rent_agreement_match": "Shop address matches rent agreement",
    "rent_address_no_match": "Shop address does not match rent agreement - check address",
    "bills_readable": "Shop bills/receipts are clear and readable",
    "bills_unreadable": "Shop bills/receipts are unclear - upload clearer photos",
    "electricity_bill_present": "Electricity bill confirms business address",
    "electricity_bill_missing": "No electricity bill provided",
    "all_checks_passed": "All verification checks passed",
    "some_checks_failed": "Some verification checks need attention",
}

# ============================================================================
# VERIFIED DATA WINDOW REASONS
# ============================================================================
# Explanation of data coverage period
VERIFIED_WINDOW_REASONS = {
    "window_6mo": "Data verified from {start} to {end} ({months} months)",
    "window_12mo": "Strong history: Data verified from {start} to {end} ({months} months)",
    "window_24mo": "Excellent history: Data verified from {start} to {end} ({months} months)",
    "window_incomplete": "Only {months} months of data available (need {required} for this tier)",
    "data_quality_high": "Data quality is high ({quality:.0f}% completeness)",
    "data_quality_medium": "Data quality is medium ({quality:.0f}% completeness)",
    "data_quality_low": "Data quality is low ({quality:.0f}% completeness) - gaps in records",
}

# ============================================================================
# GST COVERAGE REASONS
# ============================================================================
# GST filing vs actual purchases
GST_COVERAGE_REASONS = {
    "gst_coverage_high": "Your GST filings match your reported purchases {coverage:.0f}% (well organized)",
    "gst_coverage_medium": "Your GST filings match your reported purchases {coverage:.0f}% (acceptable)",
    "gst_coverage_low": "Your GST filings match your reported purchases only {coverage:.0f}% (significant gap)",
    "gst_not_registered": "Your shop is not registered for GST",
    "gst_registered_recent": "Recently registered for GST (less than {months} months history)",
    "gst_consistent": "Consistent GST reporting month-on-month",
    "gst_inconsistent": "Inconsistent GST reporting - varies significantly month-to-month",
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def generate_plain_reasons(decision_data: dict) -> list[str]:
    """
    Generate plain-language reasons for a lending decision.

    Input decision_data dict should contain:
    - tier: int (1, 2, or 3, or 0 for rejected)
    - verdict: str ('approved' or 'rejected')
    - verified_months: int (months of overlapping data)
    - source_agreement_score: float (0-1, agreement between sources)
    - photo_verified: bool (location verified from photo)
    - location_verified: bool (matches rent agreement or similar)
    - photo_count: int (number of photos submitted)
    - gst_registered: bool (has GST GSTIN)
    - gst_coverage: float (0-1, purchases matched to GST filings)
    - udyam_registered: bool (has Udyam certificate)
    - prior_repayment_history: bool or None (has paid loans on time)
    - sources_used: list[str] (['aa', 'gst', 'upi'] etc)
    - window_start_date: str or None (ISO format or None)
    - window_end_date: str or None (ISO format or None)

    Returns:
        List of plain-English reason strings.

    Example:
        >>> decision = {
        ...     'tier': 1,
        ...     'verdict': 'approved',
        ...     'verified_months': 10,
        ...     'source_agreement_score': 0.82,
        ...     'photo_verified': True,
        ...     'location_verified': True,
        ...     'gst_registered': False,
        ...     'udyam_registered': False,
        ...     'prior_repayment_history': None,
        ...     'sources_used': ['aa', 'upi'],
        ... }
        >>> reasons = generate_plain_reasons(decision)
        ['Verified 10 months of bank data...', 'Your bank and shop sales agree 82%', ...]
    """
    reasons = []

    # Extract fields with defaults
    tier = decision_data.get("tier", 0)
    verdict = decision_data.get("verdict", "rejected")
    verified_months = decision_data.get("verified_months", 0)
    source_agreement = decision_data.get("source_agreement_score", 0.0)
    photo_verified = decision_data.get("photo_verified", False)
    location_verified = decision_data.get("location_verified", False)
    gst_registered = decision_data.get("gst_registered", False)
    gst_coverage = decision_data.get("gst_coverage", 0.0)
    udyam_registered = decision_data.get("udyam_registered", False)
    prior_repayment = decision_data.get("prior_repayment_history", None)
    sources_used = decision_data.get("sources_used", [])

    # ========== DATA WINDOW COVERAGE ==========
    if verified_months >= 24:
        reasons.append(
            f"Verified {verified_months} months of bank data (excellent, well above 6 month minimum)"
        )
    elif verified_months >= 12:
        reasons.append(
            f"Verified {verified_months} months of bank data (strong history)"
        )
    elif verified_months >= 6:
        reasons.append(
            f"Verified {verified_months} months of bank data (required for this tier)"
        )
    else:
        reasons.append(
            f"Only {verified_months} months of verified data available (need 6+ months)"
        )

    # ========== SOURCE AGREEMENT ==========
    if len(sources_used) >= 3:
        reasons.append("Bank, GST, and UPI records all available")
    elif len(sources_used) == 2:
        reasons.append(f"Two data sources available: {', '.join(sources_used).upper()}")
    elif len(sources_used) == 1:
        reasons.append(f"Data from {sources_used[0].upper() if sources_used else 'one source'}")

    if source_agreement >= 0.85:
        reasons.append(
            f"Your bank and shop sales agree {source_agreement * 100:.0f}% (excellent match)"
        )
    elif source_agreement >= 0.70:
        reasons.append(
            f"Your bank and shop sales agree {source_agreement * 100:.0f}% (good match)"
        )
    elif source_agreement >= 0.60:
        reasons.append(
            f"Your bank and shop sales agree {source_agreement * 100:.0f}% (acceptable)"
        )
    else:
        reasons.append(
            f"Your bank and shop sales only agree {source_agreement * 100:.0f}% (significant gap)"
        )

    # ========== LOCATION VERIFICATION ==========
    if photo_verified and location_verified:
        reasons.append("Shop location verified with rent agreement")
    elif photo_verified:
        reasons.append("Shop location verified from geo-tagged photo")
    elif not photo_verified:
        reasons.append("Shop location could not be verified from photos")

    # ========== GST REGISTRATION & COVERAGE ==========
    if gst_registered:
        reasons.append("Shop registered for GST")
        if gst_coverage >= 0.80:
            reasons.append(
                f"GST filings match your purchases {gst_coverage * 100:.0f}% (well organized)"
            )
        elif gst_coverage >= 0.60:
            reasons.append(
                f"GST filings match your purchases {gst_coverage * 100:.0f}% (acceptable)"
            )
        else:
            reasons.append(
                f"GST filings match your purchases only {gst_coverage * 100:.0f}% (check records)"
            )
    else:
        reasons.append("Shop not registered for GST (Tier 1 eligible)")

    # ========== UDYAM REGISTRATION ==========
    if udyam_registered:
        reasons.append("Udyam (small business) certificate registered")
    elif tier >= 3:
        reasons.append("Udyam registration required for Tier 3 (10-min process at udyamregistration.gov.in)")

    # ========== PRIOR REPAYMENT HISTORY ==========
    if prior_repayment is True:
        reasons.append("Prior repayment record with us - on-time payments confirmed")
    elif tier >= 3 and prior_repayment is not True:
        reasons.append("Tier 3 requires prior on-time repayment history")

    # ========== TIER EXPLANATION ==========
    if verdict == "approved":
        if tier == 1:
            reasons.append("**Tier 1 approved**: Quick loan for emerging businesses (up to ₹50,000)")
        elif tier == 2:
            reasons.append(
                "**Tier 2 approved**: Registered business with GST compliance (up to ₹2,50,000)"
            )
        elif tier == 3:
            reasons.append(
                "**Tier 3 approved**: Established business with verified track record (up to ₹10,00,000)"
            )
    else:
        reasons.append(
            "**Decision**: Application does not yet meet criteria. See next steps below."
        )

    return reasons


def generate_next_tier_criteria(decision_data: dict) -> list[str]:
    """
    Generate plain-language explanation of what's needed for next tier.

    Returns:
        List of next-tier criteria as human-readable action items.
    """
    next_steps = []

    tier = decision_data.get("tier", 0)
    verified_months = decision_data.get("verified_months", 0)
    source_agreement = decision_data.get("source_agreement_score", 0.0)
    gst_registered = decision_data.get("gst_registered", False)
    udyam_registered = decision_data.get("udyam_registered", False)
    prior_repayment = decision_data.get("prior_repayment_history", None)
    photo_verified = decision_data.get("photo_verified", False)

    if tier == 0:
        # Rejected - general next steps
        if verified_months < 6:
            next_steps.append(
                f"Provide 6+ months of bank statement history (currently have {verified_months} months)"
            )
        if source_agreement < 0.70:
            next_steps.append(
                f"Make sure your bank records and shop sales are consistent within 20%"
            )
        if not photo_verified:
            next_steps.append(
                "Upload clear photo of shop front with geo-location and shop sign visible"
            )
        if not next_steps:
            next_steps.append("Contact support for guidance on next steps")

    elif tier == 1:
        # Tier 1 → Tier 2
        if not gst_registered:
            next_steps.append("Register for GST (free, takes 10 minutes at https://gst.gov.in)")
        else:
            next_steps.append("Accumulate 12+ months of verified bank data (currently have 6 months)")

        next_steps.append("Maintain consistent sales records across all platforms")
        next_steps.append(
            f"Make on-time EMI payments for 6+ months to build repayment history"
        )
        next_steps.append(
            "→ Then unlock **Tier 2** and borrow up to ₹2,50,000 with lower interest"
        )

    elif tier == 2:
        # Tier 2 → Tier 3
        if not udyam_registered:
            next_steps.append(
                "Register for Udyam certificate (free, 10-min process at https://udyamregistration.gov.in)"
            )
        next_steps.append("Build 24+ months of verified bank and GST data")
        next_steps.append("Maintain 6+ months of on-time EMI payments")
        next_steps.append(
            "→ Then unlock **Tier 3** and borrow up to ₹10,00,000 with industry rates"
        )

    elif tier == 3:
        # Tier 3 - maintain status
        next_steps.append("Keep all repayment EMIs on schedule")
        next_steps.append("Maintain GST registration and file returns on time")
        next_steps.append(
            "→ Unlock new tranches as you demonstrate on-time payment history"
        )

    return next_steps


def generate_source_verification_summary(decision_data: dict) -> list[str]:
    """
    Generate detailed explanation of source verification.

    Returns:
        List of explanations for each data source and how they were verified.
    """
    explanations = []

    aa_monthly = decision_data.get("aa_monthly_avg", None)
    gst_monthly = decision_data.get("gst_monthly_avg", None)
    upi_monthly = decision_data.get("upi_monthly_avg", None)
    sources_used = decision_data.get("sources_used", [])

    if "aa" in sources_used and aa_monthly:
        explanations.append(
            f"**Bank data (AA)**: Your official bank shows average monthly deposit of ₹{aa_monthly:,.0f}"
        )

    if "gst" in sources_used and gst_monthly:
        explanations.append(
            f"**GST data**: Your GST filings show average monthly turnover of ₹{gst_monthly:,.0f}"
        )

    if "upi" in sources_used and upi_monthly:
        explanations.append(
            f"**UPI data**: Your UPI transactions show average monthly volume of ₹{upi_monthly:,.0f}"
        )

    return explanations


def generate_verification_checks_summary(decision_data: dict) -> list[str]:
    """
    Generate summary of all verification checks and their status.

    Returns:
        List of verification check results in plain language.
    """
    checks = []

    photo_verified = decision_data.get("photo_verified", False)
    location_verified = decision_data.get("location_verified", False)
    gst_registered = decision_data.get("gst_registered", False)
    udyam_registered = decision_data.get("udyam_registered", False)

    if photo_verified:
        checks.append("✓ Shop location verified from photo and rent agreement")
    else:
        checks.append("✗ Shop location not yet verified")

    if gst_registered:
        checks.append("✓ GST registration confirmed")
    else:
        checks.append("◯ GST registration not required for Tier 1")

    if udyam_registered:
        checks.append("✓ Udyam certificate confirmed")
    else:
        checks.append("◯ Udyam certificate not required for Tier 1 or 2")

    return checks
