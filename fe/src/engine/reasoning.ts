/**
 * Reasoning engine: explains how loan decisions are made.
 * Pure TS, no React dependency.
 */

export interface LoanReasoning {
  amountReasons: string[]
  rateReasons: string[]
  tenorReasons: string[]
  riskFactors: string[]
  recommendations: string[]
}

export function generateLoanReasoning(input: {
  requestedAmount: number
  purpose: string
  band: 'low' | 'moderate' | 'high' | 'review'
  tenor: number
  monthlyEmi: number
  householdIncome?: number
}): LoanReasoning {
  const { requestedAmount, purpose, band, tenor, monthlyEmi, householdIncome } = input

  const amountReasons: string[] = []
  const rateReasons: string[] = []
  const tenorReasons: string[] = []
  const riskFactors: string[] = []
  const recommendations: string[] = []

  // Amount reasoning
  if (purpose === 'Stock purchase') {
    amountReasons.push(
      'Stock purchase loans are approved based on your shelf capacity and typical turnover.',
    )
    amountReasons.push(
      `₹${requestedAmount.toLocaleString('en-IN')} aligns with a 1.5× monthly COGS limit.`,
    )
  } else if (purpose === 'Festival stock') {
    amountReasons.push(
      'Festival stock loans assume short repayment cycles tied to seasonal sales peaks.',
    )
    amountReasons.push(`Your request is ₹${requestedAmount.toLocaleString('en-IN')}.`)
  } else if (purpose === 'Shop expansion') {
    amountReasons.push('Expansion loans are capped at your current stock value plus 25%.')
    amountReasons.push(`Approved amount: ₹${requestedAmount.toLocaleString('en-IN')}.`)
  } else {
    amountReasons.push(`Loan amount: ₹${requestedAmount.toLocaleString('en-IN')}.`)
    amountReasons.push('Amount is within policy caps for working capital loans.')
  }

  // Rate reasoning
  if (band === 'low') {
    rateReasons.push('Risk band: **Low.** Your stock reconciliation is solid.')
    rateReasons.push('- UPI inflows closely match implied revenue (85–115%)')
    rateReasons.push('- Multiple verified data sources agree')
    rateReasons.push('- Vintage ≥ 12 months')
    rateReasons.push('**10.5% p.a.** is the base MSME rate.')
  } else if (band === 'moderate') {
    rateReasons.push('Risk band: **Moderate.** Your data is consistent but has some gaps.')
    rateReasons.push('- UPI inflows within expected range')
    rateReasons.push('- 1–2 verified data sources')
    rateReasons.push('- Vintage ≥ 6 months')
    rateReasons.push('**14.0% p.a.** reflects the additional risk.')
  } else if (band === 'high') {
    rateReasons.push('Risk band: **High.** Your data is sparse or volatile.')
    rateReasons.push('- UPI inflows show inconsistency')
    rateReasons.push('- Single data source or conflicting sources')
    rateReasons.push('- Vintage < 6 months')
    rateReasons.push('**18.0% p.a.** is the ceiling rate.')
  } else {
    rateReasons.push('Risk band: **Under Review.** A loan officer will assess further.')
    rateReasons.push('- Data gaps or large anomalies detected')
    rateReasons.push('- Additional documentation may be needed')
    rateReasons.push('**18.0% p.a.** pending review.')
  }

  // Tenor reasoning
  if (tenor === 12) {
    tenorReasons.push('**12-month tenor** (accelerated repayment)')
    tenorReasons.push('Chosen because your monthly cashflow can support fast repayment.')
  } else if (tenor === 18) {
    tenorReasons.push('**18-month tenor** (standard repayment)')
    tenorReasons.push('Balances affordable monthly payments with timely loan closure.')
  } else {
    tenorReasons.push(`**${tenor}-month tenor** (extended repayment)`)
    tenorReasons.push('Tenor extends repayment to match your typical cash-conversion cycle.')
  }

  tenorReasons.push(
    `Monthly EMI: ₹${monthlyEmi.toLocaleString('en-IN')} — should not exceed 40% of household surplus.`,
  )

  // Risk factors
  if (band !== 'low') {
    riskFactors.push('• Data sources are limited — consider registering for UPI if you haven\'t.')
  }
  if (band === 'high' || band === 'review') {
    riskFactors.push('• Reconciliation shows gaps — manual review recommended.')
    recommendations.push('Upload purchase bills from the last 3 months to strengthen the case.')
  } else {
    riskFactors.push('✓ Stock data is consistent — low risk.')
  }

  if (householdIncome && monthlyEmi > householdIncome * 0.4) {
    riskFactors.push('• Monthly EMI is high relative to household income.')
    recommendations.push('Consider a smaller loan amount or longer tenor to reduce monthly burden.')
  }

  // Positive signals
  if (band === 'low' || band === 'moderate') {
    recommendations.push(
      'Your application is strong. Funds will be disbursed within 2 working days of approval.',
    )
  }

  if (purpose === 'Festival stock') {
    recommendations.push(
      'Festival loans are fast-tracked. Expect approval within 24 hours if data is consistent.',
    )
  }

  return { amountReasons, rateReasons, tenorReasons, riskFactors, recommendations }
}

/**
 * Generate a brief one-liner explaining why this amount was chosen.
 */
export function getAmountSummary(amount: number, purpose: string): string {
  const fmt = (n: number) =>
    '₹' +
    Math.round(n).toLocaleString('en-IN')

  if (purpose === 'Stock purchase') {
    return `Based on your shop's typical turnover and shelf capacity, you can sustain ${fmt(amount)}.`
  } else if (purpose === 'Festival stock') {
    return `Festival stocking capacity for your shop: ${fmt(amount)}.`
  } else if (purpose === 'Shop expansion') {
    return `Expansion limit (current stock + 25%): ${fmt(amount)}.`
  } else {
    return `Working capital allocation: ${fmt(amount)}.`
  }
}

/**
 * Generate a brief one-liner explaining the rate band.
 */
export function getRateSummary(band: 'low' | 'moderate' | 'high' | 'review', ratePercent: number): string {
  if (band === 'low') {
    return `Your data is solid → lowest available rate: ${ratePercent}% p.a.`
  } else if (band === 'moderate') {
    return `Your data is consistent → standard rate: ${ratePercent}% p.a.`
  } else if (band === 'high') {
    return `Your data has gaps → higher rate to offset risk: ${ratePercent}% p.a.`
  } else {
    return `Your data needs review → pending assessment: ${ratePercent}% p.a.`
  }
}
