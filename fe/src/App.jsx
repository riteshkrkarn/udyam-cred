import { useState, useRef } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import HowItWorks from './components/HowItWorks'
import Features from './components/Features'
import StockCheck from './components/StockCheck'
import Promise from './components/Promise'
import Band from './components/Band'
import Footer from './components/Footer'
import ApplyDialog from './components/dialogs/ApplyDialog'
import SignInDialog from './components/dialogs/SignInDialog'

export default function App() {
  const applyRef = useRef(null)
  const signinRef = useRef(null)

  function openDialog(id) {
    if (id === 'apply') applyRef.current?.showModal()
    if (id === 'signin') signinRef.current?.showModal()
  }

  return (
    <div className="page">
      <Header onOpen={openDialog} />
      <main>
        <Hero onOpen={openDialog} />
        <HowItWorks />
        <Features />
        <StockCheck />
        <Promise />
        <Band />
      </main>
      <Footer />
      <ApplyDialog ref={applyRef} />
      <SignInDialog ref={signinRef} />
    </div>
  )
}
