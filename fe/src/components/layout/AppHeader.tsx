import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore, getCurrentRole } from '../../features/auth/authStore'
import SignInDialog from '../../features/auth/SignInDialog'

export default function AppHeader() {
  const [navOpen, setNavOpen] = useState(false)
  const [signinOpen, setSigninOpen] = useState(false)
  const state = useAuthStore()
  const currentRole = getCurrentRole(state)
  const navigate = useNavigate()

  function close() { setNavOpen(false) }

  function handleApply() {
    close()
    navigate('/apply')
  }

  function handleDemoClick(route: string) {
    close()
    navigate(route)
  }

  const isOfficerOrAbove =
    currentRole === 'officer' ||
    currentRole === 'approver' ||
    currentRole === 'auditor'

  const isBorrower = currentRole === 'borrower'

  return (
    <>
      <header className="top">
        {/* Brand */}
        <Link className="brand" to="/" onClick={close}>
          UdyamCred
        </Link>

        {/* Mobile menu toggle */}
        <button
          className="menu-btn"
          aria-expanded={navOpen}
          aria-controls="main-nav"
          onClick={() => setNavOpen((o) => !o)}
        >
          ☰ Menu
        </button>

        {/* Nav links — role-aware */}
        <nav id="main-nav" className={navOpen ? 'open' : ''}>
          <a href="/#how" onClick={close}>
            How it works
          </a>
          <a href="/#tiers" onClick={close}>
            Tiers
          </a>
          <a href="/#safeguards" onClick={close}>
            Safeguards
          </a>
          <a href="/#trust" onClick={close}>
            Check a shop
          </a>
          <button
            type="button"
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--sheet)', font: '500 14px inherit', padding: 0 }}
            onClick={handleApply}
          >
            Apply
          </button>
        </nav>

        {/* Right-side actions */}
        <div className="header-actions" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginLeft: 'auto' }}>
          {/* Demo Buttons - Always Show */}
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              className="btn small"
              style={{ 
                background: 'rgba(255,255,255,0.15)',
                border: '1px solid rgba(255,255,255,0.3)',
                color: 'var(--sheet)',
                padding: '0.5rem 0.8rem',
                fontSize: '12px'
              }}
              onClick={() => handleDemoClick('/applications/demo_001/result')}
              title="View borrower demo"
            >
              📱 Borrower
            </button>
            <button
              className="btn small"
              style={{ 
                background: 'rgba(255,255,255,0.15)',
                border: '1px solid rgba(255,255,255,0.3)',
                color: 'var(--sheet)',
                padding: '0.5rem 0.8rem',
                fontSize: '12px'
              }}
              onClick={() => handleDemoClick('/bank/queue')}
              title="View officer queue"
            >
              👨‍💼 Queue
            </button>
            <button
              className="btn small"
              style={{ 
                background: 'rgba(255,255,255,0.15)',
                border: '1px solid rgba(255,255,255,0.3)',
                color: 'var(--sheet)',
                padding: '0.5rem 0.8rem',
                fontSize: '12px'
              }}
              onClick={() => handleDemoClick('/bank/case/demo_001')}
              title="View case details"
            >
              📋 Case
            </button>
          </div>

          {currentRole ? (
            <>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--sheet)',
                  opacity: 0.8,
                  textTransform: 'capitalize',
                  letterSpacing: '.03em',
                }}
              >
                {currentRole}{state.useDemo ? ' · demo' : ''}
              </span>
              {/* Quick jump for officer in demo */}
              {isOfficerOrAbove && state.useDemo && (
                <button
                  className="btn small"
                  style={{ color: 'var(--sheet)', borderColor: 'rgba(255,255,255,0.3)' }}
                  onClick={() => { navigate('/bank/queue'); close() }}
                >
                  → Dashboard
                </button>
              )}
              <button className="btn ghost" onClick={() => { state.signOut(); close() }}>
                Sign out
              </button>
            </>
          ) : (
            <button className="btn ghost" onClick={() => setSigninOpen(true)}>
              Sign in
            </button>
          )}
        </div>
      </header>

      <SignInDialog open={signinOpen} onClose={() => setSigninOpen(false)} />
    </>
  )
}
