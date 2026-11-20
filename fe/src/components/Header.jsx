import { useState } from 'react'

export default function Header({ onOpen }) {
  const [navOpen, setNavOpen] = useState(false)

  return (
    <header className="top">
      <a className="brand" href="#top">UdyamCred</a>
      <button
        className="menu-btn"
        aria-expanded={navOpen}
        aria-controls="nav"
        onClick={() => setNavOpen(o => !o)}
      >
        Menu
      </button>
      <nav id="nav" className={navOpen ? 'open' : ''}>
        <a href="#how-it-works" onClick={() => setNavOpen(false)}>How it works</a>
        <a href="#features" onClick={() => setNavOpen(false)}>Features</a>
        <a href="#check" onClick={() => setNavOpen(false)}>Check a shop</a>
        <a href="#" onClick={e => { e.preventDefault(); onOpen('apply') }}>Apply</a>
      </nav>
      <button className="btn ghost" onClick={() => onOpen('signin')}>Sign in</button>
    </header>
  )
}
