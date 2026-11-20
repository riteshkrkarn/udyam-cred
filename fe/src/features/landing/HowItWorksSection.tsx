import StepList from '../../components/ui/StepList'

const STEPS = [
  {
    title: 'Collect consent and basic details',
    desc: 'The shop owner agrees to share purchase bills, UPI and bank statements, and a monthly ledger page. Only these sources are used. Consent can be withdrawn at any time.',
  },
  {
    title: 'Verify the supplier exists',
    desc: 'The GSTIN on each major purchase bill is checked against the GST registry. This confirms the supplier is registered — not that the purchase happened.',
  },
  {
    title: 'Run the stock reconciliation',
    desc: "Opening stock plus purchases minus closing stock gives the cost of goods sold. Adding the shop's typical margin gives implied revenue. That is compared to the UPI inflow.",
  },
  {
    title: 'Cross-check with other sources',
    desc: 'Electricity consumption, rent paid and any available bank or ledger data are compared against the implied revenue figure to look for large gaps.',
  },
  {
    title: 'Score and decide',
    desc: 'The scorecard combines reconciliation results, source agreement and vintage into a risk band. The loan rule engine sets the amount, rate and tenor. A loan officer reviews the result and can override with a written reason.',
  },
]

export default function HowItWorksSection() {
  return (
    <section className="block narrow" id="how-it-works">
      <h2>How a shop is judged</h2>
      <p className="sub">
        A fixed pipeline, so the same input always gives the same decision. Bank auditors can
        repeat it.
      </p>
      <StepList steps={STEPS} />
    </section>
  )
}
