/**
 * Seed shop data for the demo.
 * Both shops have the same UPI inflow but different stock figures,
 * which produces different verdicts — the Stage 1 checkpoint.
 */

export interface ShopSeed {
  id: string
  name: string
  owner: string
  /** Opening stock value in rupees */
  openingStock: number
  /** Total purchases this month */
  purchases: number
  /** Closing stock value */
  closingStock: number
  /** Gross margin percentage */
  marginPct: number
  /** UPI inflow received */
  upiInflow: number
  /** Business vintage in months */
  vintageMonths: number
  gstin: string
}

export const SEED_SHOPS: ShopSeed[] = [
  {
    id: 'UC-2025-0041',
    name: 'Lakshmi Provision Store',
    owner: 'Lakshmi Devi',
    openingStock: 180_000,
    purchases: 420_000,
    closingStock: 95_000,
    marginPct: 12,
    upiInflow: 510_000,
    vintageMonths: 36,
    gstin: '27AAPFU0939F1ZV', // valid checksum for demo
  },
  {
    id: 'UC-2025-0078',
    name: 'Sri Ganesh General Stores',
    owner: 'Ganesh Kumar',
    openingStock: 210_000,
    purchases: 380_000,
    closingStock: 145_000,
    marginPct: 11,
    upiInflow: 510_000,
    vintageMonths: 24,
    gstin: '29AAPFU0939F1ZV', // different state code
  },
]
