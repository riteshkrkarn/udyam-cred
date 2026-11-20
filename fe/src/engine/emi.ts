/**
 * EMI and interest helpers.
 * All inputs are plain numbers; no React dependency.
 */

/** Monthly EMI using the standard reducing-balance formula. */
export function emi(principal: number, annualRatePct: number, months: number): number {
  const r = annualRatePct / 100 / 12
  if (r === 0) return principal / months
  return (principal * r * Math.pow(1 + r, months)) / (Math.pow(1 + r, months) - 1)
}

/** Total interest paid over the loan term. */
export function totalInterest(principal: number, annualRatePct: number, months: number): number {
  return emi(principal, annualRatePct, months) * months - principal
}

/** Full amortisation schedule: one row per month. */
export interface ScheduleRow {
  month: number
  payment: number
  principal: number
  interest: number
  balance: number
}

export function schedule(
  principal: number,
  annualRatePct: number,
  months: number,
): ScheduleRow[] {
  const r = annualRatePct / 100 / 12
  const payment = emi(principal, annualRatePct, months)
  const rows: ScheduleRow[] = []
  let balance = principal
  for (let m = 1; m <= months; m++) {
    const interest = balance * r
    const principalPart = payment - interest
    balance -= principalPart
    rows.push({
      month: m,
      payment: Math.round(payment),
      principal: Math.round(principalPart),
      interest: Math.round(interest),
      balance: Math.max(0, Math.round(balance)),
    })
  }
  return rows
}
