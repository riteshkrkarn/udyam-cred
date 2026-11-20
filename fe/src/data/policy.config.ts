/**
 * Policy configuration.
 * Caps, rate bands, and EMI share limits.
 * Keeping these in one file makes them easy to audit and update.
 */

export const POLICY = {
  /** Maximum loan amount the system will ever approve. */
  maxLoanAmount: 2_000_000,

  /** Minimum loan amount. */
  minLoanAmount: 10_000,

  /** Maximum tenor in months. */
  maxTenorMonths: 36,

  /** Minimum tenor in months. */
  minTenorMonths: 6,

  /** EMI as a share of household-adjusted monthly surplus (0–1). */
  emiShareOfSurplus: 0.4,

  /**
   * Rate bands by risk verdict.
   * Each band records the annual rate and the date the rate was set
   * (shown on the decision screen for transparency).
   */
  rateBands: {
    low: { annualRatePct: 10.5, setOn: '2025-04-01' },
    moderate: { annualRatePct: 14.0, setOn: '2025-04-01' },
    high: { annualRatePct: 18.0, setOn: '2025-04-01' },
    review: { annualRatePct: 18.0, setOn: '2025-04-01' },
  },

  /** Stock-limit multiplier: loan ≤ this × monthly COGS. */
  stockLimitMultiplier: 1.5,
} as const

export type RiskBand = keyof typeof POLICY.rateBands
