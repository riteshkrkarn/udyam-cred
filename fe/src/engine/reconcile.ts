/**
 * Stock reconciliation engine.
 * Opening stock + purchases − closing stock = COGS.
 * COGS × (1 + margin/100) = implied revenue.
 * Compare implied revenue to UPI inflow.
 */

export type Verdict = 'match' | 'review' | 'mismatch'

export interface ReconcileInput {
  openingStock: number
  purchases: number
  closingStock: number
  /** Gross margin as a percentage, e.g. 12 for 12% */
  marginPct: number
  upiInflow: number
}

export interface ReconcileResult {
  cogs: number
  impliedRevenue: number
  delta: number
  /** UPI / implied revenue */
  ratio: number
  verdict: Verdict
  comment: string
}

export function reconcile(input: ReconcileInput): ReconcileResult {
  const { openingStock, purchases, closingStock, marginPct, upiInflow } = input
  const cogs = openingStock + purchases - closingStock
  const impliedRevenue = cogs * (1 + marginPct / 100)
  const ratio = upiInflow / impliedRevenue
  const delta = upiInflow - impliedRevenue

  let verdict: Verdict
  let comment: string

  if (ratio >= 0.9 && ratio <= 1.1) {
    verdict = 'match'
    comment = 'Sales and stock figures agree within 10 %. This shop looks consistent.'
  } else if (ratio >= 0.75 && ratio < 0.9) {
    verdict = 'review'
    comment =
      'UPI inflow is below implied revenue. Could be cash sales not on UPI, or a stock overcount.'
  } else if (ratio > 1.1 && ratio <= 1.3) {
    verdict = 'review'
    comment =
      'UPI inflow exceeds implied revenue. Could be advance payments or transfers not related to sales.'
  } else {
    verdict = 'mismatch'
    comment =
      'Large gap between sales and stock. Needs manual review before proceeding.'
  }

  return { cogs, impliedRevenue, delta, ratio, verdict, comment }
}
