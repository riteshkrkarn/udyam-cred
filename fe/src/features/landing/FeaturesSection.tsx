import { useState } from 'react'
import StatusTag from '../../components/ui/StatusTag'

interface FeatureItem {
  title: string
  sub: string
  live: boolean
}

interface FeatureGroup {
  label: string
  desc: string
  items: FeatureItem[]
}

const GROUPS: FeatureGroup[] = [
  {
    label: 'Reconciliation engine',
    desc: 'The core pipeline that checks whether sales match stock.',
    items: [
      {
        title: 'Stock reconciliation',
        sub: 'Opening + purchases − closing vs UPI inflow',
        live: true,
      },
      {
        title: 'Margin adjustment',
        sub: 'Apply shop-reported margin to cost of goods sold',
        live: true,
      },
      {
        title: 'GSTIN format validator',
        sub: 'Checks supplier GSTIN format and checksum',
        live: true,
      },
      {
        title: 'Round-trip detection',
        sub: 'Flag circular money flows between counterparties',
        live: false,
      },
    ],
  },
  {
    label: 'Credit scoring',
    desc: 'Models and rules that turn reconciliation results into a decision.',
    items: [
      { title: 'UPI-only baseline model', sub: 'Logistic regression for comparison', live: false },
      {
        title: 'Credibility scorecard',
        sub: 'Main model with risk bands and reason codes',
        live: false,
      },
      {
        title: 'Confidence calculation',
        sub: 'Based on how much sources agree',
        live: false,
      },
      {
        title: 'Vintage engine',
        sub: 'Earliest date supported by two sources',
        live: false,
      },
    ],
  },
  {
    label: 'Loan rules',
    desc: 'Rules that set the amount, rate and repayment schedule.',
    items: [
      {
        title: 'Loan amount rule',
        sub: 'Lowest of repayment capacity, stock and policy limits',
        live: false,
      },
      {
        title: 'Rate band engine',
        sub: 'Starting band from MSME rates, adjusted by risk',
        live: false,
      },
      { title: 'EMI cap', sub: 'Fixed share of household-adjusted surplus', live: false },
      {
        title: 'Fund split rules',
        sub: 'Fixed split across stock, buffer, expansion, reserve',
        live: false,
      },
    ],
  },
  {
    label: 'Transparency and audit',
    desc: 'Every decision is explainable and reversible by a person.',
    items: [
      {
        title: 'Reason codes',
        sub: 'Plain-language reasons from model weights',
        live: false,
      },
      { title: 'Replay view', sub: 'Change an input and see the result move', live: false },
      {
        title: 'Override workflow',
        sub: 'Loan officer override with written reason, logged',
        live: false,
      },
      {
        title: 'Audit record API',
        sub: 'All decisions and overrides are stored and queryable',
        live: false,
      },
    ],
  },
]

export default function FeaturesSection() {
  const [filter, setFilter] = useState<'all' | 'live'>('all')

  return (
    <section className="block" id="features">
      <h2>What is in the product</h2>
      <p className="sub">
        Every feature planned for the MVP is listed here. Items marked{' '}
        <strong>Working now</strong> are already in this build.
      </p>

      <div className="filter" role="group" aria-label="Filter features">
        <button
          className={`btn small${filter === 'all' ? ' on' : ''}`}
          onClick={() => setFilter('all')}
        >
          All
        </button>
        <button
          className={`btn small${filter === 'live' ? ' on' : ''}`}
          onClick={() => setFilter('live')}
        >
          Working now
        </button>
      </div>

      <div id="feat-list">
        {GROUPS.map((g) => {
          const hasLive = g.items.some((i) => i.live)
          if (filter === 'live' && !hasLive) return null

          return (
            <div key={g.label} className={`group${filter === 'live' ? ' only-live' : ''}`}>
              <div className="gh">
                <h3>{g.label}</h3>
                <p>{g.desc}</p>
              </div>
              <ul className="list" style={{ listStyle: 'none', margin: 0 }}>
                {g.items.map((item) => (
                  <li key={item.title} className={`row${item.live ? ' live' : ''}`}>
                    <div>
                      <b>{item.title}</b>
                      <span>{item.sub}</span>
                    </div>
                    <StatusTag status={item.live ? 'live' : 'soon'} />
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </section>
  )
}
