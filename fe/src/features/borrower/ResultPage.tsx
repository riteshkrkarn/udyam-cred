import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { useApplyStore } from './applyStore'
import Sheet from '../../components/ui/Sheet'
import ReasoningBox from '../../components/ui/ReasoningBox'
import { emi, schedule } from '../../engine/emi'
import { POLICY } from '../../data/policy.config'
import { generateLoanReasoning, getAmountSummary, getRateSummary } from '../../engine/reasoning'

function fmt(n: number) {
  return '₹' + Math.round(n).toLocaleString('en-IN')
}

export default function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const { applicationId, draft } = useApplyStore()
  const [showSchedule, setShowSchedule] = useState(false)

  // Guard: if the ID doesn't match the stored application, show a message
  if (!applicationId || applicationId !== id || !draft.amount) {
    return (
      <div style={{ padding: '4rem 0', maxWidth: 480 }}>
        <p className="eyebrow">Result</p>
        <h2>Application not found</h2>
        <p className="sub" style={{ marginTop: '0.5rem' }}>
          This application does not exist or the data was cleared.
        </p>
        <div className="actions" style={{ marginTop: '2rem' }}>
          <Link className="btn green" to="/apply">
            Start a new application
          </Link>
        </div>
      </div>
    )
  }

  // Placeholder scoring: a simple rule based on the amount requested
  // This will be replaced with the full scorecard engine in Stage 2.
  const amount = draft.amount!
  const purpose = draft.purpose || 'Working capital'
  const band: 'low' | 'moderate' | 'high' | 'review' = 'moderate'
  const rateConfig = POLICY.rateBands[band]
  const months = 18
  const monthlyEmi = emi(amount, rateConfig.annualRatePct, months)

  // Generate reasoning
  const reasoning = generateLoanReasoning({
    requestedAmount: amount,
    purpose,
    band,
    tenor: months,
    monthlyEmi,
  })

  const amountSummary = getAmountSummary(amount, purpose)
  const rateSummary = getRateSummary(band, rateConfig.annualRatePct)

  // Amortisation schedule
  const scheduleRows = schedule(amount, rateConfig.annualRatePct, months)
  const totalInterest = scheduleRows.reduce((sum, row) => sum + row.interest, 0)

  return (
    <div style={{ maxWidth: 640, padding: '3rem 0' }}>
      <p className="eyebrow">Application {id}</p>
      <h1 style={{ fontSize: 'clamp(1.5rem, 3vw, 2rem)', marginBottom: '0.5rem' }}>
        Your indicative loan offer
      </h1>
      <p className="sub" style={{ marginBottom: '2rem' }}>
        This is a placeholder demonstrating how decisions are explained. A real assessment will
        include your stock data, UPI history, and bank records.
      </p>

      {/* Main offer summary */}
      <Sheet>
        <h3>Offer Summary</h3>
        <table className="rows">
          <tbody>
            <tr>
              <td>Application ID</td>
              <td>{id}</td>
            </tr>
            <tr>
              <td>Loan amount</td>
              <td style={{ fontWeight: 700, color: 'var(--green)' }}>{fmt(amount)}</td>
            </tr>
            <tr>
              <td>Annual interest rate</td>
              <td style={{ fontWeight: 700, color: 'var(--green)' }}>
                {rateConfig.annualRatePct}% p.a.
              </td>
            </tr>
            <tr>
              <td>Repayment tenor</td>
              <td>{months} months</td>
            </tr>
            <tr className="total">
              <td>Monthly EMI</td>
              <td style={{ fontWeight: 700, color: 'var(--bad)' }}>{fmt(monthlyEmi)}</td>
            </tr>
          </tbody>
        </table>

        <div className="foot" style={{ marginTop: '1.5rem' }}>
          <p className="note">
            Rate set on {rateConfig.setOn}. Funds will be credited to your account within 2 working
            days of approval.
          </p>
        </div>
      </Sheet>

      {/* Decision reasoning */}
      <Sheet style={{ marginTop: '2rem' }}>
        <h3>How we reached this offer</h3>
        <p className="note" style={{ marginBottom: '1.5rem' }}>
          Click each section to see the reasoning behind each decision.
        </p>

        <div style={{ marginBottom: '1rem', padding: '0.75rem', background: 'rgba(242, 244, 236, 0.8)', borderRadius: 4 }}>
          <p style={{ margin: 0, fontSize: 14, color: 'var(--sec)' }}>
            📋 <strong>Purpose:</strong> {purpose}
          </p>
        </div>

        <ReasoningBox
          title="💰 Loan Amount"
          items={reasoning.amountReasons}
          expanded
        />

        <ReasoningBox
          title="📊 Interest Rate"
          items={reasoning.rateReasons}
          expanded
        />

        <ReasoningBox
          title="⏳ Repayment Period"
          items={reasoning.tenorReasons}
          expanded
        />

        {reasoning.riskFactors.length > 0 && (
          <ReasoningBox
            title="⚠️ Risk Assessment"
            items={reasoning.riskFactors}
            expanded={false}
          />
        )}

        {reasoning.recommendations.length > 0 && (
          <ReasoningBox
            title="💡 Recommendations"
            items={reasoning.recommendations}
            expanded={false}
          />
        )}
      </Sheet>

      {/* Repayment schedule */}
      <Sheet style={{ marginTop: '2rem' }}>
        <h3>Repayment Schedule</h3>
        <p className="note" style={{ marginBottom: '1rem' }}>
          Your monthly payment plan over {months} months.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <p style={{ fontSize: 12, color: 'var(--sec)', margin: 0 }}>Total to repay</p>
            <p style={{ fontSize: 18, fontWeight: 700, color: 'var(--ink)', margin: 0 }}>
              {fmt(amount + totalInterest)}
            </p>
          </div>
          <div>
            <p style={{ fontSize: 12, color: 'var(--sec)', margin: 0 }}>Total interest</p>
            <p style={{ fontSize: 18, fontWeight: 700, color: 'var(--bad)', margin: 0 }}>
              {fmt(totalInterest)}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowSchedule(!showSchedule)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--green)',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: 14,
            padding: 0,
            textDecoration: showSchedule ? 'underline' : 'none',
          }}
        >
          {showSchedule ? '▼ Hide' : '▶ View'} month-by-month breakdown
        </button>

        {showSchedule && (
          <div style={{ marginTop: '1rem', overflowX: 'auto' }}>
            <table className="rows" style={{ fontSize: 12 }}>
              <tbody>
                <tr>
                  <td style={{ textAlign: 'left', fontWeight: 600, borderBottom: '2px solid var(--rule)' }}>
                    Month
                  </td>
                  <td
                    style={{
                      textAlign: 'right',
                      fontWeight: 600,
                      borderBottom: '2px solid var(--rule)',
                    }}
                  >
                    Payment
                  </td>
                  <td
                    style={{
                      textAlign: 'right',
                      fontWeight: 600,
                      borderBottom: '2px solid var(--rule)',
                    }}
                  >
                    Principal
                  </td>
                  <td
                    style={{
                      textAlign: 'right',
                      fontWeight: 600,
                      borderBottom: '2px solid var(--rule)',
                    }}
                  >
                    Interest
                  </td>
                  <td
                    style={{
                      textAlign: 'right',
                      fontWeight: 600,
                      borderBottom: '2px solid var(--rule)',
                    }}
                  >
                    Balance
                  </td>
                </tr>
                {scheduleRows.map((row, i) => (
                  <tr key={i} className={i === scheduleRows.length - 1 ? 'total' : ''}>
                    <td>{row.month}</td>
                    <td style={{ textAlign: 'right' }}>{fmt(row.payment)}</td>
                    <td style={{ textAlign: 'right' }}>{fmt(row.principal)}</td>
                    <td style={{ textAlign: 'right', color: 'var(--bad)' }}>{fmt(row.interest)}</td>
                    <td style={{ textAlign: 'right' }}>{fmt(row.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Sheet>

      {/* Call to action */}
      <div className="actions" style={{ marginTop: '2rem' }}>
        <Link className="btn red" to="/">
          Accept & Continue
        </Link>
        <Link className="btn small" to="/apply">
          Modify Application
        </Link>
      </div>

      <p style={{ fontSize: 12, color: 'var(--sec)', marginTop: '2rem', textAlign: 'center' }}>
        A loan officer will review your application and contact you within 24 hours.
      </p>
    </div>
  )
}
