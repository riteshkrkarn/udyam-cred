import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Header({ onOpen }) {
  const [navOpen, setNavOpen] = useState(false)
  const navigate = useNavigate()

  const handleDemoClick = (route) => {
    setNavOpen(false)
    navigate(route)
  }

  return (
    <header className="top">
      <div className="header-left">
        <a className="brand" href="#top">
          <span className="brand-icon">💰</span>
          UdyamCred
        </a>
      </div>

      <button
        className="menu-btn"
        aria-expanded={navOpen}
        aria-controls="nav"
        onClick={() => setNavOpen(o => !o)}
      >
        ☰ Menu
      </button>

      <nav id="nav" className={navOpen ? 'open' : ''}>
        <a href="#how-it-works" onClick={() => setNavOpen(false)}>How it works</a>
        <a href="#features" onClick={() => setNavOpen(false)}>Features</a>
        <a href="#check" onClick={() => setNavOpen(false)}>Check a shop</a>
        <a href="#" onClick={e => { e.preventDefault(); onOpen('apply') }}>Apply</a>
      </nav>

      <div className="header-actions">
        {/* Demo Buttons */}
        <div className="demo-buttons">
          <button 
            className="btn demo-borrower"
            title="View borrower application result page"
            onClick={() => handleDemoClick('/applications/demo_001/result')}
          >
            📱 Borrower Demo
          </button>
          
          <button 
            className="btn demo-officer"
            title="View bank officer dashboard"
            onClick={() => handleDemoClick('/bank/queue')}
          >
            👨‍💼 Officer Dashboard
          </button>

          <button 
            className="btn demo-case"
            title="View officer case details"
            onClick={() => handleDemoClick('/bank/case/demo_001')}
          >
            📋 View Case
          </button>
        </div>

        <button className="btn ghost" onClick={() => onOpen('signin')}>Sign in</button>
      </div>
    </header>
  )
}
