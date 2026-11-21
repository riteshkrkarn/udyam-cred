/**
 * Glossary Data: Plain-language definitions of lending terms
 * Mirrors backend app/templates/glossary.py
 */

export interface GlossaryEntry {
  term: string
  category: string
  definition: string
  example: string
  relatedTerms?: string[]
}

export const glossaryEntries: GlossaryEntry[] = [
  // Lending Tiers
  {
    term: 'Tier 1',
    category: 'Lending Tiers',
    definition:
      'Loans up to ₹50,000 for emerging businesses with 6+ months of bank data. Repaid in 12 months.',
    example:
      'Rajesh has 10 months of bank data showing ₹80K monthly sales. He qualifies for Tier 1 (up to ₹50K).',
    relatedTerms: ['Tier 2', 'Tier 3'],
  },
  {
    term: 'Tier 2',
    category: 'Lending Tiers',
    definition:
      'Loans up to ₹2,50,000 for established businesses registered for GST with 12+ months verified history. Repaid in 24 months in 2-3 tranches.',
    example:
      'Priya is registered for GST with 18 months of filing history. She qualifies for Tier 2 (up to ₹2.5L).',
    relatedTerms: ['Tier 1', 'Tier 3', 'Tranche'],
  },
  {
    term: 'Tier 3',
    category: 'Lending Tiers',
    definition:
      'Loans up to ₹10,00,000 for large established businesses with Udyam registration, 24+ months GST history, and prior on-time repayment record with us. Repaid in 36 months in 4+ tranches.',
    example:
      'Vikram has Udyam, 30 months of GST filings, and repaid our previous loan on time. He qualifies for Tier 3 (up to ₹10L).',
    relatedTerms: ['Tier 1', 'Tier 2', 'Udyam', 'Tranche'],
  },

  // Loan Structure
  {
    term: 'Tranche',
    category: 'Loan Structure',
    definition:
      'A portion of your loan that is released on a specific date. Instead of giving you the full amount at once, we release it in parts to verify you\'re using the money for your business.',
    example:
      'Priya gets ₹2,50,000 in 2 tranches: ₹1,50,000 now, and ₹1,00,000 after 60 days if her shop sales stay healthy.',
    relatedTerms: ['EMI', 'Repayment'],
  },
  {
    term: 'EMI',
    category: 'Loan Structure',
    definition:
      'Equated Monthly Installment—the fixed amount you pay every month to repay your loan. It includes both principal (money you borrowed) and interest.',
    example:
      'Rajesh borrows ₹50,000 at 18.5% interest. His EMI is ₹3,800/month for 12 months.',
    relatedTerms: ['Principal', 'Interest', 'Tranche'],
  },
  {
    term: 'Principal',
    category: 'Loan Structure',
    definition:
      'The amount of money you actually borrowed. Your EMI pays down the principal + interest each month.',
    example:
      'Rajesh borrows ₹50,000 (principal). His EMI includes ₹3,400 principal repayment + ₹400 interest.',
    relatedTerms: ['Interest', 'EMI'],
  },
  {
    term: 'Interest',
    category: 'Loan Structure',
    definition:
      'The fee you pay for borrowing money from us. Expressed as an annual percentage (APR). Tier 1 gets 18.5%, Tier 2 gets 14%, Tier 3 gets 11%.',
    example:
      'Rajesh borrows ₹50K at 18.5% APR. He pays ₹400 interest in month 1 (and less each month as principal shrinks).',
    relatedTerms: ['Principal', 'APR', 'EMI'],
  },
  {
    term: 'APR',
    category: 'Loan Structure',
    definition:
      'Annual Percentage Rate—the yearly interest rate on your loan. We quote APR so you can compare with other lenders.',
    example:
      'Rajesh\'s loan has an 18.5% APR. Over 12 months, that\'s about ₹4,500 in total interest.',
    relatedTerms: ['Interest', 'EMI'],
  },

  // Verification
  {
    term: 'Source Agreement',
    category: 'Verification',
    definition:
      'A measure of how well your sales data matches across different sources (bank, GST, UPI). High agreement = we trust your numbers more.',
    example:
      'Rajesh\'s bank shows ₹85K monthly sales, UPI shows ₹90K, and GST shows ₹88K. These agree well (82% agreement), so we trust him more.',
    relatedTerms: ['Account Aggregator', 'GST Filings', 'Verified Window'],
  },
  {
    term: 'Verified Window',
    category: 'Verification',
    definition:
      'The time period during which we have bank, GST, and/or UPI data from your business. Longer verified windows mean safer loans.',
    example:
      'Rajesh has bank data from March to December (10 months). This 10-month window shows us a good picture of his sales patterns.',
    relatedTerms: ['Source Agreement', 'Account Aggregator'],
  },
  {
    term: 'Photo Verification',
    category: 'Verification',
    definition:
      'We ask you to take 3 live photos of your shop (front, stock, bills) with a handwritten random code visible. This proves your business is real and located where you say.',
    example:
      'Rajesh writes "ABC123" on paper, holds it in front of his shop, and takes a photo. We verify the code, location, and shop condition.',
    relatedTerms: ['Verified Window', 'Location Verified'],
  },
  {
    term: 'Location Verified',
    category: 'Verification',
    definition:
      'Your shop location (from photos) matches your rent agreement or lease address. This confirms you actually run the business at that location.',
    example:
      'Rajesh\'s rent agreement says "123 Main St, Bangalore." His shop photo is geo-tagged at exactly that address, so location is verified.',
    relatedTerms: ['Photo Verification', 'Verified Window'],
  },

  // Data Sources
  {
    term: 'Account Aggregator',
    category: 'Data Sources',
    definition:
      'A safe, government-approved way to share your bank account data with us—without giving us your password or banking app access.',
    example:
      'Instead of telling us your bank password, you use Account Aggregator to securely share 12 months of your bank statements with us in 2 minutes.',
    relatedTerms: ['GST Filings', 'UPI Data'],
  },
  {
    term: 'GST Filings',
    category: 'Data Sources',
    definition:
      'Government GST (Goods & Services Tax) returns (GSTR-2B) that show your business turnover. We use this to verify your sales are real.',
    example:
      'Priya files GST every month. Her GSTR-2B shows ₹1,00,000 in annual sales—which matches her bank data, so we trust it more.',
    relatedTerms: ['Source Agreement', 'Account Aggregator', 'Udyam'],
  },
  {
    term: 'UPI Data',
    category: 'Data Sources',
    definition:
      'Digital payment transactions from UPI (Google Pay, PhonePe, etc.). Shows money flowing into your business from customers.',
    example:
      'Rajesh gets ₹50K in UPI payments monthly from customers. This data strengthens his loan application.',
    relatedTerms: ['Account Aggregator', 'Source Agreement'],
  },

  // Registration
  {
    term: 'Udyam',
    category: 'Registration',
    definition:
      'A free government registration for micro, small, and medium enterprises (MSMEs). Takes 10 minutes online and helps you qualify for larger loans.',
    example:
      'Vikram registered his shop as a Udyam enterprise. This boosted his application to Tier 3 eligibility.',
    relatedTerms: ['Tier 3', 'GST Filings'],
  },
  {
    term: 'GST Registration',
    category: 'Registration',
    definition:
      'Government registration for Goods & Services Tax. Required if your business turnover exceeds ₹20,00,000 annually. Mandatory for Tier 2 & 3 loans.',
    example:
      'Priya registered for GST after her shop sales crossed ₹30L annually. Now she qualifies for Tier 2 loans.',
    relatedTerms: ['Tier 2', 'Tier 3', 'Udyam'],
  },

  // Repayment
  {
    term: 'Repayment',
    category: 'Repayment',
    definition:
      'Paying back your loan monthly via EMI. On-time repayment helps you qualify for larger loans (higher tiers) in the future.',
    example:
      'Rajesh pays ₹3,800 every 20th of the month. After 12 on-time payments, he\'ll qualify for Tier 2 (up to ₹2.5L) on his next application.',
    relatedTerms: ['EMI', 'Stop Rule', 'Tier'],
  },
  {
    term: 'Stop Rule',
    category: 'Repayment',
    definition:
      'If you miss 2 EMI payments, your account is frozen and no more tranches are released until a bank officer reviews your situation.',
    example:
      'Priya misses her January and February EMIs. In March, her Tier 2 loan is frozen and she can\'t access the 2nd tranche until she talks to our team.',
    relatedTerms: ['Tranche', 'EMI', 'Repayment'],
  },
  {
    term: 'On-Time Payment',
    category: 'Repayment',
    definition:
      'You pay your EMI by the due date. On-time payments build your repayment history and help you qualify for higher tiers.',
    example:
      'Rajesh\'s EMI is due on the 20th. He pays on the 18th, so his payment is marked as "on-time."',
    relatedTerms: ['EMI', 'Repayment'],
  },
  {
    term: 'Late Payment',
    category: 'Repayment',
    definition: 'You pay your EMI after the due date but within a grace period (usually 10 days).',
    example:
      'Rajesh\'s EMI is due on the 20th, but he pays on the 25th. His payment is marked as "late" but the account is still active.',
    relatedTerms: ['EMI', 'Stop Rule'],
  },
  {
    term: 'Missed Payment',
    category: 'Repayment',
    definition:
      'You don\'t pay your EMI within the grace period. If you miss 2 EMIs, your account is frozen (Stop Rule).',
    example:
      'Rajesh\'s EMI is due on the 20th. He doesn\'t pay by the 30th (end of grace period). This EMI is marked as "missed."',
    relatedTerms: ['Late Payment', 'Stop Rule', 'Frozen Account'],
  },
  {
    term: 'Frozen Account',
    category: 'Repayment',
    definition:
      'Your account is temporarily frozen after 2+ missed EMI payments. No new tranches are released. You need to talk to our team to unfreeze it.',
    example:
      'Priya missed 2 EMIs. Her account is now frozen and she can\'t access the next tranche of her Tier 2 loan.',
    relatedTerms: ['Stop Rule', 'Missed Payment', 'Tranche'],
  },
]

/**
 * Get glossary entry by term name
 */
export function getGlossaryEntry(term: string): GlossaryEntry | undefined {
  return glossaryEntries.find(e => e.term.toLowerCase() === term.toLowerCase())
}

/**
 * Get all glossary categories
 */
export function getGlossaryCategories(): string[] {
  return Array.from(new Set(glossaryEntries.map(e => e.category))).sort()
}

/**
 * Get glossary entries by category
 */
export function getGlossaryByCategory(category: string): GlossaryEntry[] {
  return glossaryEntries.filter(e => e.category === category)
}

/**
 * Search glossary entries
 */
export function searchGlossary(query: string): GlossaryEntry[] {
  const lowerQuery = query.toLowerCase()
  return glossaryEntries.filter(
    e =>
      e.term.toLowerCase().includes(lowerQuery) ||
      e.definition.toLowerCase().includes(lowerQuery) ||
      e.example.toLowerCase().includes(lowerQuery)
  )
}
