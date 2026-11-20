import { useState } from 'react'
import InterestCalc from './InterestCalc'
import MissedChances from './MissedChances'
import Slips from './Slips'

export default function Hero({ onOpen }) {
  return (
    <section className="hero" id="top">
      <div className="margin">
        <p className="eyebrow">Bahi-Khata Stock &amp; Credit Reconciliation Protocol</p>
        <h1>No credit score. Higher interest, or no loan at all.</h1>
        <p className="lead">
          A shop can sell every day and still have no credit history. Banks turn it away, or the owner
          borrows from informal lenders at a much higher rate. Meanwhile the chances pass by: the festival
          stock that could not be bought early, the fridge that was never added. UdyamCred judges a shop
          by what it actually does. It checks that the stock bought, the goods sold and the money received
          all agree.
        </p>
        <div className="actions">
          <button className="btn red" onClick={() => onOpen('apply')}>Apply for a loan</button>
          <a className="btn green" href="#check">Check a shop's stock</a>
        </div>
      </div>

      <div className="grid2 indent">
        <InterestCalc />
        <MissedChances />
      </div>

      <div className="indent leadin">
        <h2>Same UPI inflow. Different verdict.</h2>
        <p>Both shops below received ₹5,10,000 on UPI. Only one of them sold what its shelves could support.</p>
      </div>
      <div className="grid2 indent">
        <Slips />
      </div>
    </section>
  )
}
