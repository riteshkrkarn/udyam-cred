/**
 * Demo Banner: Shows this is a demo/preview environment
 * Displays at top of page for both borrower and officer demo sections
 */

import './DemoBanner.css'

export default function DemoBanner({ type = 'default', message }) {
  const messages = {
    borrower: 'Demo: Borrower Application Result Page',
    officer: 'Demo: Bank Officer Dashboard - Application Queue',
    case: 'Demo: Bank Officer Case Review Console',
    default: 'UdyamCred Phase 1-2 Demo Environment'
  }

  return (
    <div className={`demo-banner banner-${type}`}>
      <div className="demo-banner-content">
        <span className="demo-badge">🎬 DEMO</span>
        <p>{message || messages[type]}</p>
        <button 
          className="demo-close"
          onClick={() => window.location.href = '/'}
          title="Return to home"
        >
          Return Home
        </button>
      </div>
    </div>
  )
}
