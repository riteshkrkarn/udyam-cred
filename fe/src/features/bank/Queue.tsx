/**
 * Queue View: Application processing queue for bank officers
 * Shows pending applications grouped by tier with status filters
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Sheet from '../../components/ui/Sheet'
import './Queue.css'

interface QueueItem {
  application_id: string
  borrower_name: string
  tier: number
  amount_requested: number
  status: string
  created_at: string
  stage: number
  documents_complete: boolean
  location_verified: boolean
  photo_count: number
}

const STATUS_COLORS = {
  pending: '#FFA500',
  scored: '#4169E1',
  tier_1: '#90EE90',
  tier_2: '#87CEEB',
  tier_3: '#DDA0DD',
  frozen: '#FF6B6B',
  completed: '#228B22',
}

const STATUS_LABELS = {
  pending: 'Pending Review',
  scored: 'Scored',
  tier_1: 'Tier 1',
  tier_2: 'Tier 2',
  tier_3: 'Tier 3',
  frozen: 'Frozen',
  completed: 'Completed',
}

const QUEUE_STAGES = [
  { num: 1, label: 'Docs Incomplete', icon: '📋' },
  { num: 2, label: 'Ready to Score', icon: '✓' },
  { num: 3, label: 'Scored', icon: '🎯' },
  { num: 4, label: 'Tier Assigned', icon: '📊' },
  { num: 5, label: 'Tranche Pending', icon: '💰' },
  { num: 6, label: 'Repayment', icon: '📅' },
  { num: 7, label: 'Completed', icon: '✅' },
]

interface QueueStats {
  total_pending: number
  tier_1_count: number
  tier_2_count: number
  tier_3_count: number
  frozen_count: number
}

export default function Queue() {
  const navigate = useNavigate()
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [stats, setStats] = useState<QueueStats>({
    total_pending: 0,
    tier_1_count: 0,
    tier_2_count: 0,
    tier_3_count: 0,
    frozen_count: 0,
  })
  const [filter, setFilter] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'created' | 'amount' | 'tier'>('created')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadQueue()
  }, [])

  async function loadQueue() {
    try {
      setLoading(true)
      // TODO: Replace with API call
      // const response = await fetch('/api/dashboard/queue')
      // const data = await response.json()
      
      // Mock data for development
      const mockQueue: QueueItem[] = [
        {
          application_id: 'app_001',
          borrower_name: 'Rajesh Kumar',
          tier: 1,
          amount_requested: 50000,
          status: 'tier_1',
          created_at: '2024-11-15',
          stage: 4,
          documents_complete: true,
          location_verified: true,
          photo_count: 3,
        },
        {
          application_id: 'app_002',
          borrower_name: 'Priya Sharma',
          tier: 2,
          amount_requested: 200000,
          status: 'scored',
          created_at: '2024-11-18',
          stage: 3,
          documents_complete: true,
          location_verified: false,
          photo_count: 3,
        },
        {
          application_id: 'app_003',
          borrower_name: 'Vikram Singh',
          tier: 3,
          amount_requested: 500000,
          status: 'tier_3',
          created_at: '2024-11-20',
          stage: 5,
          documents_complete: true,
          location_verified: true,
          photo_count: 3,
        },
        {
          application_id: 'app_004',
          borrower_name: 'Anjali Patel',
          tier: 1,
          amount_requested: 35000,
          status: 'pending',
          created_at: '2024-11-19',
          stage: 2,
          documents_complete: false,
          location_verified: false,
          photo_count: 2,
        },
        {
          application_id: 'app_005',
          borrower_name: 'Arjun Desai',
          tier: 2,
          amount_requested: 150000,
          status: 'frozen',
          created_at: '2024-11-10',
          stage: 6,
          documents_complete: true,
          location_verified: true,
          photo_count: 3,
        },
      ]

      setQueue(mockQueue)
      setStats({
        total_pending: mockQueue.length,
        tier_1_count: mockQueue.filter(q => q.tier === 1).length,
        tier_2_count: mockQueue.filter(q => q.tier === 2).length,
        tier_3_count: mockQueue.filter(q => q.tier === 3).length,
        frozen_count: mockQueue.filter(q => q.status === 'frozen').length,
      })
    } catch (error) {
      console.error('Failed to load queue:', error)
    } finally {
      setLoading(false)
    }
  }

  function getFilteredQueue(): QueueItem[] {
    let filtered = queue

    if (filter !== 'all') {
      if (filter === 'frozen') {
        filtered = filtered.filter(q => q.status === 'frozen')
      } else {
        const tierNum = parseInt(filter.split('_')[1])
        filtered = filtered.filter(q => q.tier === tierNum)
      }
    }

    if (sortBy === 'amount') {
      filtered = [...filtered].sort((a, b) => b.amount_requested - a.amount_requested)
    } else if (sortBy === 'tier') {
      filtered = [...filtered].sort((a, b) => b.tier - a.tier)
    } else {
      filtered = [...filtered].sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    }

    return filtered
  }

  function handleRowClick(applicationId: string) {
    navigate(`/bank/case/${applicationId}`)
  }

  const filteredQueue = getFilteredQueue()

  return (
    <Sheet>
      <div className="queue-container">
        {/* Header */}
        <div className="queue-header">
          <h1>Application Queue</h1>
          <button className="btn small" onClick={loadQueue}>
            Refresh
          </button>
        </div>

        {/* Stats Cards */}
        <div className="queue-stats">
          <div className="stat-card">
            <div className="stat-label">Total Pending</div>
            <div className="stat-value">{stats.total_pending}</div>
          </div>
          <div className="stat-card" style={{ borderColor: '#90EE90' }}>
            <div className="stat-label">Tier 1</div>
            <div className="stat-value">{stats.tier_1_count}</div>
          </div>
          <div className="stat-card" style={{ borderColor: '#87CEEB' }}>
            <div className="stat-label">Tier 2</div>
            <div className="stat-value">{stats.tier_2_count}</div>
          </div>
          <div className="stat-card" style={{ borderColor: '#DDA0DD' }}>
            <div className="stat-label">Tier 3</div>
            <div className="stat-value">{stats.tier_3_count}</div>
          </div>
          <div className="stat-card" style={{ borderColor: '#FF6B6B' }}>
            <div className="stat-label">Frozen</div>
            <div className="stat-value">{stats.frozen_count}</div>
          </div>
        </div>

        {/* Filter & Sort Controls */}
        <div className="queue-controls">
          <div className="control-group">
            <label>Filter:</label>
            <select 
              value={filter} 
              onChange={(e) => setFilter(e.target.value)}
              className="select"
            >
              <option value="all">All Applications</option>
              <option value="tier_1">Tier 1</option>
              <option value="tier_2">Tier 2</option>
              <option value="tier_3">Tier 3</option>
              <option value="frozen">Frozen Accounts</option>
            </select>
          </div>

          <div className="control-group">
            <label>Sort by:</label>
            <select 
              value={sortBy} 
              onChange={(e) => setSortBy(e.target.value as any)}
              className="select"
            >
              <option value="created">Date (Newest)</option>
              <option value="amount">Amount (High to Low)</option>
              <option value="tier">Tier (High to Low)</option>
            </select>
          </div>
        </div>

        {/* Queue Stages Legend */}
        <div className="queue-stages-legend">
          <p style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>Pipeline Stages:</p>
          <div className="stages-row">
            {QUEUE_STAGES.map(stage => (
              <div key={stage.num} className="stage-badge">
                <span className="stage-icon">{stage.icon}</span>
                <span className="stage-label">{stage.num}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Queue Table */}
        {loading ? (
          <p style={{ textAlign: 'center', padding: '2rem' }}>Loading...</p>
        ) : filteredQueue.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '2rem', color: '#999' }}>
            No applications found.
          </p>
        ) : (
          <div className="queue-table">
            <table>
              <thead>
                <tr>
                  <th>Borrower Name</th>
                  <th>Tier</th>
                  <th>Amount</th>
                  <th>Stage</th>
                  <th>Status</th>
                  <th>Docs</th>
                  <th>Location</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredQueue.map(item => (
                  <tr 
                    key={item.application_id}
                    onClick={() => handleRowClick(item.application_id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ fontWeight: '600' }}>{item.borrower_name}</td>
                    <td>
                      <span className="badge" style={{
                        backgroundColor: item.tier === 1 ? '#90EE90' : 
                                        item.tier === 2 ? '#87CEEB' : '#DDA0DD'
                      }}>
                        Tier {item.tier}
                      </span>
                    </td>
                    <td>₹{item.amount_requested.toLocaleString()}</td>
                    <td style={{ fontSize: '0.9rem' }}>
                      {QUEUE_STAGES[item.stage - 1]?.icon} {item.stage}
                    </td>
                    <td>
                      <span className="badge" style={{ backgroundColor: STATUS_COLORS[item.status as keyof typeof STATUS_COLORS] }}>
                        {STATUS_LABELS[item.status as keyof typeof STATUS_LABELS]}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {item.documents_complete ? '✓' : '✗'}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {item.location_verified ? '✓' : '✗'}
                    </td>
                    <td style={{ fontSize: '0.85rem', color: '#666' }}>
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <span style={{ color: '#0066cc' }}>→</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Summary */}
        <div className="queue-summary">
          <p>Showing {filteredQueue.length} of {queue.length} applications</p>
        </div>
      </div>
    </Sheet>
  )
}
