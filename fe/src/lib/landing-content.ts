export type TierId = 1 | 2 | 3;

export interface TierPolicy {
  id: TierId;
  name: string;
  tagline: string;
  needs: string[];
  maxAmount: number;
  tenureMonths: number;
  tranches: number[];     // share of the loan per tranche
  trancheDays: number[];  // days after approval
  adjustment: number;     // percentage points added to the industry rate
  nextStep: string | null;
}

export const TIERS: TierPolicy[] = [
  {
    id: 1,
    name: "Tier 1",
    tagline: "A first loan for shops building a record",
    needs: [
      "6 or more months of bank data and UPI records",
      "Bank and UPI sales agree by more than 70%",
      "Shop photo with code, matched to your rent address",
    ],
    maxAmount: 50000,
    tenureMonths: 12,
    tranches: [1],
    trancheDays: [0],
    adjustment: 4,
    nextStep: "Register for GST and build 12 months of verified history to reach Tier 2.",
  },
  {
    id: 2,
    name: "Tier 2",
    tagline: "For GST-registered shops with a year of history",
    needs: [
      "12 or more months of verified bank data",
      "GST registered, with filings we can read",
      "Shop location verified",
    ],
    maxAmount: 250000,
    tenureMonths: 24,
    tranches: [0.6, 0.4],
    trancheDays: [0, 60],
    adjustment: 2,
    nextStep: "Register for Udyam and repay on time to reach Tier 3.",
  },
  {
    id: 3,
    name: "Tier 3",
    tagline: "For established shops with a repayment record with us",
    needs: [
      "24 or more months of bank data with GST",
      "Udyam registered",
      "A repayment record with UdyamCred",
    ],
    maxAmount: 1000000,
    tenureMonths: 36,
    tranches: [0.4, 0.3, 0.2, 0.1],
    trancheDays: [0, 60, 120, 180],
    adjustment: 0,
    nextStep: null,
  },
];

// Illustrative defaults from the plan. Live values come from the dated rate table.
export const INDUSTRY_RATES: Record<TierId, number> = { 1: 14.5, 2: 12.0, 3: 10.5 };
export const RATES_NOTE =
  "Rates shown use illustrative industry rates. The bank team sets real ones and each decision records the date used.";

export const tierRate = (id: TierId): number =>
  INDUSTRY_RATES[id] + (TIERS.find((t) => t.id === id)?.adjustment ?? 0);

export const TRUSTED_SOURCES = [
  {
    name: "Bank statements through Account Aggregator",
    weight: 60,
    note: "Shared from your bank with your consent. You cannot edit it.",
  },
  {
    name: "GST filings",
    weight: 30,
    note: "Taken from the filings on record. You cannot edit them.",
  },
  {
    name: "UPI records",
    weight: 10,
    note: "Counted least, because personal and shop payments can mix.",
  },
];

export const CROSS_CHECK_ONLY = [
  "Purchase bills you upload",
  "Your daily ledger",
  "Household budget you enter",
];

export const GLOSSARY = [
  {
    term: "Tier",
    meaning:
      "Your loan level. It rises as more of your history is verified. Example: a shop with 10 months of bank data starts at Tier 1.",
  },
  {
    term: "Tranche",
    meaning:
      "A part of the loan paid out in stages. The next part is released only if earlier EMIs were paid on time.",
  },
  {
    term: "EMI",
    meaning:
      "The fixed amount you repay each month, covering part of the loan and the interest.",
  },
  {
    term: "Account Aggregator",
    meaning:
      "A regulated way to share your bank data with a lender, only with your consent, and you can stop sharing later.",
  },
  {
    term: "Udyam",
    meaning:
      "The government registration for micro, small and medium businesses. It is free to apply and unlocks Tier 3.",
  },
  {
    term: "GSTR-2B",
    meaning:
      "A monthly statement, drawn up from your suppliers' filings, of the purchases and tax credit available to a GST-registered business.",
  },
  {
    term: "Sales verification",
    meaning:
      "Our check that your bank, GST and UPI records tell the same story about your monthly sales.",
  },
];
