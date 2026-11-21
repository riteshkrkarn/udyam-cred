/**
 * Queue View: Application processing queue for bank officers
 * Fetches from the real backend at /bank/queue with a mock fallback for demo mode.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Sheet from '../../components/ui/Sheet'
import { useBankQueue } from '../../api/queries'
import './Queue.css'

// ── Types ────────────────────────────────────────────────────────────────────

interface QueueRow {
  id: string
  borrower_name: string
  tier: number
  amount: number
  status: string
  created_at: string
}

// ── Mock data (used when backend is unavailable) ─────────────────────────────

const MOCK_QUEUE: QueueRow[] = [
  { id: 'app_001', borrower_name: 'Rajesh Kumar',   tier: 1, amount: 50000,  status: 'tier_1', created_at: '2024-11-15' },
  { id: 'app_002', borrower_name: 'Priya Sharma',   tier: 2, amount: 200000, status: 'scored', created_at: '2024-11-18' },
  { id: 'app_003', borrower_name: 'Vikram Singh',   tier: 3, amount: 500000, status: 'tier_3', created_at: '2024-11-20' },
  { id: 'app_004', borrower_name: 'Anjali Patel',   tier: 1, amount: 35000,  status: 'pending',created_at: '2024-11-19' },
  { id: 'app_005', borrower_name: 'Arjun Desai',    tier: 2, amount: 150000, status: 'frozen', created_at: '2024-11-10' },
]

const STATUS_COLOR: Record<string, string> = {
  pending:   '#FFA500',
  scored:    '#4169E1',
  tier_1:    '#90EE90',
  tier_2:    '#87CEEB',
  tier_3:    '#DDA0DD',
  frozen:    '#FF6B6B',
  completed: '#228B22',
  verified:  '#4169E1',
  approved:  '#90EE90',
  rejected:  '#FF6B6B',
}

// ── Component ────────────────────────────────────────────────────────────────

export default function Queue() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState('all')
  const [sortBy, setSortBy] = useState<'created' | 'amount' | 'tier'>('created')

  // Try live backend first; fall back to mock on error
  const { data, isLoading, isError, refetch } = useBankQueue()

  // Build display rows from either real or mock data
  const rawRows: QueueRow[] = isError || !data
    ? MOCK_QUEUE
    : data.applications.map((a) => ({
        id: String(a.id),
        borrower_name: `Application #${a.id}`,
        tier: 1,                     // tier not in list endpoint yet
        amount: a.amount_requested ?? 0,
        status: a.status,
        created_at: a.created_at,
      }))

  // Filter
  const filtered = rawRows.filter((r) => {
    if (filter === 'all') return true
    if (filter === 'frozen') return r.status === 'frozen'
    const t = parseInt(filter.replace('tier_', ''))
    return r.tier === t
  })

  // Sort
  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === 'amount') return b.amount - a.amount
    if (sortBy === 'tier')   return b.tier - a.tier
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  const counts = {
    total:  rawRows.length,
    tier1:  rawRows.filter((r) => r.tier === 1).length,
    tier2:  rawRows.filter((r) => r.tier === 2).length,
    tier3:  rawRows.filter((r) => r.tier === 3).length,
    frozen: rawRows.filter((r) => r.status === 'frozen').length,
  }

  return (
    <Sheet>
      <div className="queue-container">
        {/* Header */}
        <div className="queue-header">
          <h1>Bank Dashboard — Application Queue</h1>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            {isError && (
              <span style={{ fontSize: 12, color: '#FFA500' }}>
                ⚠ Backend offline — showing demo data
              </span>
            )}
            {!isError && !isLoading && (
              <span style={{ fontSize: 12, color: 'var(--ok)' }}>
                ✓ Live data from backend
              </span>
            )}
            <button className="btn small" onClick={() => refetch()}>
              Refresh
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="queue-stats">
          {[
            { label: 'Total',  value: counts.total,  color: 'var(--rule)' },
            { label: 'Tier 1', value: counts.tier1,  color: '#90EE90' },
            { label: 'Tier 2', value: counts.tier2,  color: '#87CEEB' },
            { label: 'Tier 3', value: counts.tier3,  color: '#DDA0DD' },
            { label: 'Frozen', value: counts.frozen, color: '#FF6B6B' },
          ].map((s) => (
            <div key={s.label} className="stat-card" style={{ borderColor: s.color }}>
              <div className="stat-label">{s.label}</div>
              <div className="stat-value">{s.value}</div>
            </div>
          ))}
        </div>

        {/* Controls */}
        <div className="queue-controls">
          <div className="control-group">
            <label>Filter:</label>
            <select value={filter} onChange={(e) => setFilter(e.target.value)} className="select">
              <option value="all">All</option>
              <option value="tier_1">Tier 1</option>
              <option value="tier_2">Tier 2</option>
              <option value="tier_3">Tier 3</option>
              <option value="frozen">Frozen</option>
            </select>
          </div>
          <div className="control-group">
            <label>Sort:</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} className="select">
              <option value="created">Date (newest)</option>
              <option value="amount">Amount (high→low)</option>
              <option value="tier">Tier (high→low)</option>
            </select>
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <p style={{ textAlign: 'center', padding: '2rem' }}>Loading…</p>
        ) : sorted.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '2rem', color: '#999' }}>No applications found.</p>
        ) : (
          <div className="queue-table">
            <table>
              <thead>
                <tr>
                  <th>Borrower</th>
                  <th>Tier</th>
                  <th>Amount requested</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => navigate(`/bank/case/${item.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ fontWeight: 600 }}>{item.borrower_name}</td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          backgroundColor:
                            item.tier === 1 ? '#90EE90' :
                            item.tier === 2 ? '#87CEEB' : '#DDA0DD',
                        }}
                      >
                        Tier {item.tier}
                      </span>
                    </td>
                    <td>₹{item.amount.toLocaleString('en-IN')}</td>
                    <td>
                      <span
                        className="badge"
                        style={{ backgroundColor: STATUS_COLOR[item.status] ?? '#ddd' }}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem', color: '#666' }}>
                      {new Date(item.created_at).toLocaleDateString('en-IN')}
                    </td>
                    <td style={{ color: '#0066cc' }}>→</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="queue-summary">
          <p>Showing {sorted.length} of {rawRows.length} applications</p>
        </div>
      </div>
    </Sheet>
  )
}
