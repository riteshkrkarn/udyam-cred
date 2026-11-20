import { useState } from 'react'
import { fmt, totalInterest } from '../utils/finance'

export default function InterestCalc() {
  const [amt, setAmt] = useState(200000)
  const [mon, setMon] = useState(18)
  const [r1, setR1] = useState(16)
  const [r2, setR2] = useState(36)

  const i1 = totalInterest(amt, r1, mon)
  const i2 = totalInterest(amt, r2, mon)
  const diff = i2 - i1

  return (
    <article className="sheet">
      <h3>What it costs in interest</h3>
      <p className="note">Move the sliders. Rates are illustrative, not quotes.</p>

      <label>Loan amount <output>{fmt(amt)}</output>
        <input type="range" min="50000" max="1000000" step="10000" value={amt}
          onChange={e => setAmt(Number(e.target.value))} />
      </label>

      <label>Months to repay <output>{mon}</output>
        <input type="range" min="6" max="36" step="1" value={mon}
          onChange={e => setMon(Number(e.target.value))} />
      </label>

      <label>Bank rate, verified shop <output>{r1}%</output>
        <input type="range" min="9" max="24" step="0.5" value={r1}
          onChange={e => setR1(Number(e.target.value))} />
      </label>

      <label>Informal lender rate <output>{r2}%</output>
        <input type="range" min="24" max="60" step="1" value={r2}
          onChange={e => setR2(Number(e.target.value))} />
      </label>

      <table className="rows">
        <tbody>
          <tr><td>Bank loan</td><td>{fmt(i1)}</td></tr>
          <tr><td>Informal lender</td><td>{fmt(i2)}</td></tr>
          <tr className="total">
            <td>Extra paid for having no record</td>
            <td className="bad">{fmt(diff)}</td>
          </tr>
        </tbody>
      </table>
    </article>
  )
}
