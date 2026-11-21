/**
 * Glossary: Slide-over modal with plain-language term definitions
 * Accessible from any screen via button or context
 */

import { useState, useMemo } from 'react'
import './Glossary.css'

interface GlossaryTerm {
  term: string
  definition: string
  example: string
  category: string
  relatedTerms?: string[]
}

const GLOSSARY_TERMS: GlossaryTerm[] = [
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
    term: 'Principal',
    category: 'Loan Terms',
    definition: 'The amount of money you actually borrowed. Your EMI pays down the principal + interest each month.',
    example: 'Rajesh borrows ₹50,000 (principal). His EMI includes ₹3,400 principal repayment + ₹400 interest.',
    relatedTerms: ['Interest', 'EMI'],
  },
  {
    term: 'Interest',
    category: 'Loan Terms',
    definition:
      'The fee you pay for borrowing money from us. Expressed as an annual percentage (APR). Tier 1 gets 18.5%, Tier 2 gets 14%, Tier 3 gets 11%.',
    example:
      'Rajesh borrows ₹50K at 18.5% APR. He pays ₹400 interest in month 1 (and less each month as principal shrinks).',
    relatedTerms: ['Principal', 'APR', 'EMI'],
  },
  {
    term: 'APR',
    category: 'Loan Terms',
    definition: 'Annual Percentage Rate—the yearly interest rate on your loan. We quote APR so you can compare with other lenders.',
    example: 'Rajesh\'s loan has an 18.5% APR. Over 12 months, that\'s about ₹4,500 in total interest.',
    relatedTerms: ['Interest', 'EMI'],
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
    term: 'Repayment',
    category: 'Repayment',
    definition: 'Paying back your loan monthly via EMI. On-time repayment helps you qualify for larger loans (higher tiers) in the future.',
    example:
      'Rajesh pays ₹3,800 every 20th of the month. After 12 on-time payments, he\'ll qualify for Tier 2 (up to ₹2.5L) on his next application.',
    relatedTerms: ['EMI', 'Stop Rule', 'Tier'],
  },
]

interface GlossaryProps {
  onClose?: () => void
  highlightTerm?: string
}

export default function Glossary({ onClose, highlightTerm }: GlossaryProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [expandedTerm, setExpandedTerm] = useState<string | null>(highlightTerm || null)

  const categories = useMemo(
    () => Array.from(new Set(GLOSSARY_TERMS.map(t => t.category))).sort(),
    []
  )

  const filteredTerms = useMemo(() => {
    return GLOSSARY_TERMS.filter(term => {
      const matchesSearch =
        term.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
        term.definition.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesCategory = !selectedCategory || term.category === selectedCategory
      return matchesSearch && matchesCategory
    })
  }, [searchTerm, selectedCategory])

  return (
    <div className="glossary-overlay" onClick={onClose}>
      <div className="glossary-modal" onClick={(e) => e.stopPropagation()}>
        <div className="glossary-header">
          <h2>Glossary</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="glossary-search">
          <input
            type="text"
            placeholder="Search terms..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="glossary-categories">
          <button
            className={`category-btn ${!selectedCategory ? 'active' : ''}`}
            onClick={() => setSelectedCategory(null)}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              className={`category-btn ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="glossary-terms">
          {filteredTerms.length === 0 ? (
            <p style={{ textAlign: 'center', color: '#999', padding: '2rem' }}>
              No terms found. Try a different search.
            </p>
          ) : (
            filteredTerms.map(term => (
              <div
                key={term.term}
                className={`glossary-item ${expandedTerm === term.term ? 'expanded' : ''}`}
              >
                <button
                  className="term-header"
                  onClick={() =>
                    setExpandedTerm(expandedTerm === term.term ? null : term.term)
                  }
                >
                  <span className="term-name">{term.term}</span>
                  <span className="category-badge">{term.category}</span>
                  <span className="expand-icon">
                    {expandedTerm === term.term ? '▼' : '▶'}
                  </span>
                </button>

                {expandedTerm === term.term && (
                  <div className="term-content">
                    <p className="definition">
                      <strong>Definition:</strong> {term.definition}
                    </p>
                    <p className="example">
                      <strong>Example:</strong> {term.example}
                    </p>
                    {term.relatedTerms && term.relatedTerms.length > 0 && (
                      <p className="related">
                        <strong>Related:</strong>{' '}
                        {term.relatedTerms.map((t, idx) => (
                          <button
                            key={t}
                            className="related-link"
                            onClick={() => setExpandedTerm(t)}
                          >
                            {t}
                            {idx < term.relatedTerms!.length - 1 ? ', ' : ''}
                          </button>
                        ))}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
