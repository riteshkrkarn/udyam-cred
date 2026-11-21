/**
 * Case View: Detailed application review for a single borrower
 * Shows source agreement, tier reasoning, photo verification, tranche plan, and repayment status
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Sheet from '../../components/ui/Sheet'
import Glossary from '../../components/Glossary'
import './CaseView.css'

interface Decision {
  decision_id: string
  tier: number
  approved_amount: number
  rate_percent: number
  verified_months: number
  source_agreement_score: number
  location_verified: boolean
  photo_count: number
  reasons: string[]
  next_tier_criteria: string[]
  tranche_plan: TranchePlan[]
  emi_schedule: EMI[]
}

interface TranchePlan {
  tranche_num: number
  amount: number
  release_date: string
  status: 'pending' | 'released' | 'repaid'
}

interface EMI {
  month: number
  amount: number
  principal: number
  interest: number
  paid_date?: string
  status?: 'pending' | 'ontime' | 'late' | 'missed'
}

interface Photo {
  photo_id: string
  photo_type: string
  photo_path: string
  location_lat: number
  location_lng: number
  verification_status: string
  timestamp: string
}

interface SourceAgreement {
  weighted_sales: number
  aa_weight: number
  gst_weight: number
  upi_weight: number
  agreement_score: number
  sources_used: string[]
  confidence: string
}

interface CaseData {
  application_id: string
  borrower_name: string
  borrower_phone: string
  created_at: string
  decision: Decision
  photos: Photo[]
  source_agreement: SourceAgreement
  documents: { name: string; status: string }[]
}

const TIER_COLORS = {
  1: '#90EE90',
  2: '#87CEEB',
  3: '#DDA0DD',
}

export default function CaseView() {
  const { applicationId } = useParams<{ applicationId: string }>()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState<CaseData | null>(null)
  const [loading, setLoading] = useState(true)
  const [showGlossary, setShowGlossary] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'sources' | 'photos' | 'documents' | 'repayment'>('overview')
  const [showReplayConsole, setShowReplayConsole] = useState(false)

  useEffect(() => {
    loadCaseData()
  }, [applicationId])

  async function loadCaseData() {
    try {
      setLoading(true)
      // TODO: Replace with API call
      // const response = await fetch(`/api/applications/${applicationId}`)
      // const data = await response.json()

      // Mock data for development
      const mockData: CaseData = {
        application_id: applicationId || 'app_001',
        borrower_name: 'Rajesh Kumar',
        borrower_phone: '+91-98765-43210',
        created_at: '2024-11-15',
        decision: {
          decision_id: 'dec_001',
          tier: 1,
          approved_amount: 41000,
          rate_percent: 18.5,
          verified_months: 10,
          source_agreement_score: 0.82,
          location_verified: true,
          photo_count: 3,
          reasons: [
            'Verified 10 months of bank data (requires 6+)',
            'AA and UPI agree on sales 82%',
            'Shop location verified with rent agreement',
            'Not registered for GST (Tier 2 requires it)',
          ],
          next_tier_criteria: [
            'Register for GST to qualify for Tier 2 loans (up to ₹2.5L)',
            'Maintain 6+ months of on-time repayment',
            'Increase verified history to 12 months',
          ],
          tranche_plan: [
            {
              tranche_num: 1,
              amount: 41000,
              release_date: '2024-11-20',
              status: 'released',
            },
          ],
          emi_schedule: [
            { month: 1, amount: 3800, principal: 3400, interest: 400, status: 'ontime', paid_date: '2024-12-20' },
            { month: 2, amount: 3800, principal: 3400, interest: 400, status: 'ontime', paid_date: '2025-01-20' },
            { month: 3, amount: 3800, principal: 3400, interest: 400, status: 'pending' },
          ],
        },
        photos: [
          {
            photo_id: 'photo_001',
            photo_type: 'Shop Front',
            photo_path: '/photos/shop_front.jpg',
            location_lat: 12.9716,
            location_lng: 77.5946,
            verification_status: 'verified',
            timestamp: '2024-11-15T10:30:00Z',
          },
          {
            photo_id: 'photo_002',
            photo_type: 'Stock Shelves',
            photo_path: '/photos/stock.jpg',
            location_lat: 12.9716,
            location_lng: 77.5946,
            verification_status: 'verified',
            timestamp: '2024-11-15T10:35:00Z',
          },
          {
            photo_id: 'photo_003',
            photo_type: 'Bills/Ledger',
            photo_path: '/photos/bills.jpg',
            location_lat: 12.9716,
            location_lng: 77.5946,
            verification_status: 'verified',
            timestamp: '2024-11-15T10:40:00Z',
          },
        ],
        source_agreement: {
          weighted_sales: 82500,
          aa_weight: 0.6,
          gst_weight: 0.3,
          upi_weight: 0.1,
          agreement_score: 0.82,
          sources_used: ['aa', 'upi'],
          confidence: 'medium',
        },
        documents: [
          { name: 'Electricity Bill', status: 'uploaded' },
          { name: 'Udyam Certificate', status: 'not_provided' },
          { name: 'GST Return', status: 'not_provided' },
        ],
      }

      setCaseData(mockData)
    } catch (error) {
      console.error('Failed to load case data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Sheet>
        <p style={{ textAlign: 'center', padding: '2rem' }}>Loading case data...</p>
      </Sheet>
    )
  }

  if (!caseData) {
    return (
      <Sheet>
        <p style={{ textAlign: 'center', padding: '2rem', color: '#999' }}>Case not found</p>
      </Sheet>
    )
  }

  const { decision } = caseData
  const tierColor = TIER_COLORS[decision.tier as keyof typeof TIER_COLORS]

  return (
    <Sheet>
      <div className="case-view-container">
        {/* Header */}
        <div className="case-header">
          <div className="case-title">
            <button className="back-btn" onClick={() => navigate('/bank/queue')}>←</button>
            <h1>{caseData.borrower_name}</h1>
            <span className="tier-badge" style={{ backgroundColor: tierColor }}>
              Tier {decision.tier}
            </span>
          </div>
          <div className="case-metadata">
            <p><strong>Phone:</strong> {caseData.borrower_phone}</p>
            <p><strong>Application ID:</strong> {caseData.application_id}</p>
            <p><strong>Applied:</strong> {new Date(caseData.created_at).toLocaleDateString()}</p>
          </div>
        </div>

        {/* Decision Summary */}
        <div className="case-decision-box">
          <h2>Decision Summary</h2>
          <div className="decision-grid">
            <div className="decision-item">
              <span className="label">Approved Amount</span>
              <span className="value">₹{decision.approved_amount.toLocaleString()}</span>
            </div>
            <div className="decision-item">
              <span className="label">Interest Rate</span>
              <span className="value">{decision.rate_percent}% APR</span>
            </div>
            <div className="decision-item">
              <span className="label">Verified Months</span>
              <span className="value">{decision.verified_months}</span>
            </div>
            <div className="decision-item">
              <span className="label">Source Agreement</span>
              <span className="value">{(decision.source_agreement_score * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* Decision Reasons */}
          <div className="decision-reasons">
            <h3>Why this tier?</h3>
            <ul>
              {decision.reasons.map((reason, idx) => (
                <li key={idx}>
                  {reason}
                  <button 
                    className="glossary-link"
                    onClick={() => setShowGlossary(true)}
                    title="Open glossary"
                  >
                    ?
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Next Tier Criteria */}
          <div className="next-tier">
            <h3>How to reach next tier</h3>
            <ul style={{ color: '#666' }}>
              {decision.next_tier_criteria.map((criterion, idx) => (
                <li key={idx}>{criterion}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Tabs */}
        <div className="case-tabs">
          <button
            className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            className={`tab ${activeTab === 'sources' ? 'active' : ''}`}
            onClick={() => setActiveTab('sources')}
          >
            Source Agreement
          </button>
          <button
            className={`tab ${activeTab === 'photos' ? 'active' : ''}`}
            onClick={() => setActiveTab('photos')}
          >
            Photos ({caseData.photos.length})
          </button>
          <button
            className={`tab ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            Documents
          </button>
          <button
            className={`tab ${activeTab === 'repayment' ? 'active' : ''}`}
            onClick={() => setActiveTab('repayment')}
          >
            Repayment
          </button>
        </div>

        {/* Tab Content */}
        <div className="case-tab-content">
          {activeTab === 'overview' && (
            <div className="tab-pane">
              <h3>Tranche Plan</h3>
              <table className="tranche-table">
                <thead>
                  <tr>
                    <th>Tranche #</th>
                    <th>Amount</th>
                    <th>Release Date</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {decision.tranche_plan.map(tranche => (
                    <tr key={tranche.tranche_num}>
                      <td>{tranche.tranche_num}</td>
                      <td>₹{tranche.amount.toLocaleString()}</td>
                      <td>{new Date(tranche.release_date).toLocaleDateString()}</td>
                      <td>
                        <span className="badge" style={{
                          backgroundColor: tranche.status === 'released' ? '#90EE90' : 
                                          tranche.status === 'repaid' ? '#228B22' : '#FFA500'
                        }}>
                          {tranche.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <h3 style={{ marginTop: '2rem' }}>Loan Details</h3>
              <div className="loan-details">
                <p><strong>Tenor:</strong> 12 months</p>
                <p><strong>Monthly EMI:</strong> ₹{decision.emi_schedule[0]?.amount.toLocaleString() || 'N/A'}</p>
                <p><strong>Photos Verified:</strong> {caseData.photos.length}/3</p>
                <p><strong>Location Match:</strong> {decision.location_verified ? '✓ Verified' : '✗ Not verified'}</p>
              </div>
            </div>
          )}

          {activeTab === 'sources' && (
            <div className="tab-pane">
              <h3>Source Agreement Analysis</h3>
              <div className="source-agreement-box">
                <div className="agreement-metric">
                  <span>Agreement Score</span>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill"
                      style={{ width: `${caseData.source_agreement.agreement_score * 100}%` }}
                    ></div>
                  </div>
                  <span>{(caseData.source_agreement.agreement_score * 100).toFixed(0)}%</span>
                </div>

                <div className="source-weights">
                  <h4>Data Sources & Weights</h4>
                  {caseData.source_agreement.sources_used.includes('aa') && (
                    <div className="source-item">
                      <span>AA Bank Data</span>
                      <span className="weight">{(caseData.source_agreement.aa_weight * 100).toFixed(0)}%</span>
                      <span className="bar" style={{ 
                        backgroundImage: `linear-gradient(90deg, #4169E1 0%, #4169E1 ${caseData.source_agreement.aa_weight * 100}%, #eee ${caseData.source_agreement.aa_weight * 100}%, #eee 100%)`
                      }}></span>
                    </div>
                  )}
                  {caseData.source_agreement.sources_used.includes('gst') && (
                    <div className="source-item">
                      <span>GST Filings</span>
                      <span className="weight">{(caseData.source_agreement.gst_weight * 100).toFixed(0)}%</span>
                      <span className="bar" style={{ 
                        backgroundImage: `linear-gradient(90deg, #FF8C00 0%, #FF8C00 ${caseData.source_agreement.gst_weight * 100}%, #eee ${caseData.source_agreement.gst_weight * 100}%, #eee 100%)`
                      }}></span>
                    </div>
                  )}
                  {caseData.source_agreement.sources_used.includes('upi') && (
                    <div className="source-item">
                      <span>UPI Data</span>
                      <span className="weight">{(caseData.source_agreement.upi_weight * 100).toFixed(0)}%</span>
                      <span className="bar" style={{ 
                        backgroundImage: `linear-gradient(90deg, #9370DB 0%, #9370DB ${caseData.source_agreement.upi_weight * 100}%, #eee ${caseData.source_agreement.upi_weight * 100}%, #eee 100%)`
                      }}></span>
                    </div>
                  )}
                </div>

                <p style={{ marginTop: '1rem', color: '#666', fontSize: '0.9rem' }}>
                  <strong>Confidence:</strong> {caseData.source_agreement.confidence.charAt(0).toUpperCase() + caseData.source_agreement.confidence.slice(1)}
                  — sources agree well on monthly sales (₹{caseData.source_agreement.weighted_sales.toLocaleString()})
                </p>
              </div>
            </div>
          )}

          {activeTab === 'photos' && (
            <div className="tab-pane">
              <h3>Photo Verification</h3>
              <div className="photos-grid">
                {caseData.photos.map(photo => (
                  <div key={photo.photo_id} className="photo-card">
                    <img src={photo.photo_path} alt={photo.photo_type} />
                    <div className="photo-info">
                      <p><strong>{photo.photo_type}</strong></p>
                      <p style={{ fontSize: '0.8rem', color: '#666' }}>
                        {new Date(photo.timestamp).toLocaleString()}
                      </p>
                      <p style={{ fontSize: '0.8rem', color: '#666' }}>
                        📍 {photo.location_lat.toFixed(4)}, {photo.location_lng.toFixed(4)}
                      </p>
                      <span className="badge" style={{
                        backgroundColor: photo.verification_status === 'verified' ? '#90EE90' : '#FFA500',
                        marginTop: '0.5rem'
                      }}>
                        {photo.verification_status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="tab-pane">
              <h3>Documents</h3>
              <table className="documents-table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {caseData.documents.map((doc, idx) => (
                    <tr key={idx}>
                      <td>{doc.name}</td>
                      <td>
                        <span className="badge" style={{
                          backgroundColor: doc.status === 'uploaded' ? '#90EE90' : '#ddd',
                          color: doc.status === 'uploaded' ? '#333' : '#999'
                        }}>
                          {doc.status === 'uploaded' ? '✓ Uploaded' : '○ Not provided'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'repayment' && (
            <div className="tab-pane">
              <h3>EMI Schedule</h3>
              <table className="emi-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>EMI Amount</th>
                    <th>Principal</th>
                    <th>Interest</th>
                    <th>Status</th>
                    <th>Paid Date</th>
                  </tr>
                </thead>
                <tbody>
                  {decision.emi_schedule.map(emi => (
                    <tr key={emi.month}>
                      <td>{emi.month}</td>
                      <td>₹{emi.amount.toLocaleString()}</td>
                      <td>₹{emi.principal.toLocaleString()}</td>
                      <td>₹{emi.interest.toLocaleString()}</td>
                      <td>
                        <span className="badge" style={{
                          backgroundColor: emi.status === 'ontime' ? '#90EE90' : 
                                          emi.status === 'pending' ? '#FFA500' : '#FF6B6B'
                        }}>
                          {emi.status}
                        </span>
                      </td>
                      <td>{emi.paid_date ? new Date(emi.paid_date).toLocaleDateString() : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Officer Actions */}
        <div className="case-actions">
          <button 
            className="btn small"
            onClick={() => setShowReplayConsole(!showReplayConsole)}
          >
            {showReplayConsole ? 'Close Replay' : 'Replay Scoring'}
          </button>
          <button className="btn small" style={{ backgroundColor: '#FF6B6B' }}>
            Override Decision
          </button>
          <button 
            className="btn small"
            onClick={() => setShowGlossary(!showGlossary)}
          >
            Glossary
          </button>
        </div>

        {/* Replay Console */}
        {showReplayConsole && (
          <VerificationConsole applicationId={caseData.application_id} />
        )}

        {/* Glossary Modal */}
        {showGlossary && (
          <Glossary onClose={() => setShowGlossary(false)} />
        )}
      </div>
    </Sheet>
  )
}

// Verification/Replay Console
function VerificationConsole({ applicationId }: { applicationId: string }) {
  const [replayData, setReplayData] = useState({
    verified_months: 10,
    source_agreement_score: 0.82,
    location_verified: true,
    photo_count: 3,
    gst_registered: false,
  })

  async function replayScoring() {
    // TODO: Call API to replay scoring with modified data
    console.log('Replaying scoring with:', replayData)
  }

  return (
    <div className="replay-console">
      <h3>Replay Scoring</h3>
      <div className="replay-inputs">
        <label>
          Verified Months:
          <input
            type="number"
            value={replayData.verified_months}
            onChange={(e) => setReplayData({ ...replayData, verified_months: parseInt(e.target.value) })}
            min="0"
            max="36"
          />
        </label>
        <label>
          Source Agreement:
          <input
            type="number"
            value={replayData.source_agreement_score}
            onChange={(e) => setReplayData({ ...replayData, source_agreement_score: parseFloat(e.target.value) })}
            min="0"
            max="1"
            step="0.01"
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={replayData.location_verified}
            onChange={(e) => setReplayData({ ...replayData, location_verified: e.target.checked })}
          />
          Location Verified
        </label>
        <label>
          <input
            type="checkbox"
            checked={replayData.gst_registered}
            onChange={(e) => setReplayData({ ...replayData, gst_registered: e.target.checked })}
          />
          GST Registered
        </label>
      </div>
      <button className="btn small" onClick={replayScoring}>Replay</button>
    </div>
  )
}
