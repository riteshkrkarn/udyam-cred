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

  function close() {
    setNavOpen(false)
  }

  function handleApply() {
    close()
    navigate('/apply')
  }

  function handleSignOut() {
    state.signOut()
    close()
  }

  return (
    <>
      <header className="top">
        <Link className="brand" to="/" onClick={close}>
          UdyamCred
        </Link>
        <button
          className="menu-btn"
          aria-expanded={navOpen}
          aria-controls="main-nav"
          onClick={() => setNavOpen((o) => !o)}
        >
          Menu
        </button>
        <nav id="main-nav" className={navOpen ? 'open' : ''}>
          <a href="/#how-it-works" onClick={close}>
            How it works
          </a>
          <a href="/#features" onClick={close}>
            Features
          </a>
          <a href="/#check" onClick={close}>
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
        {currentRole ? (
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: 'var(--sheet)', opacity: 0.75 }}>
              {currentRole} {state.useDemo && '(demo)'}
            </span>
            <button className="btn ghost" onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        ) : (
          <button className="btn ghost" onClick={() => setSigninOpen(true)}>
            Sign in
          </button>
        )}
      </header>
      <SignInDialog open={signinOpen} onClose={() => setSigninOpen(false)} />
    </>
  )
}
