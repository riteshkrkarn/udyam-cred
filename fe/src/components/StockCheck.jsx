import { useState } from 'react'

const DEMOS = [
  { name: 'Lakshmi', open: 180000, buy: 420000, close: 95000, margin: 12, upi: 510000 },
  { name: 'Sri Ganesh', open: 210000, buy: 380000, close: 145000, margin: 11, upi: 510000 },
]

function fmt(n) {
  return '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN')
}

function validateGSTIN(g) {
  const re = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/
  if (!re.test(g)) return { ok: false, msg: 'Format invalid. Expected pattern: 27AAPFU0939F1ZV' }
  // checksum
  const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  let sum = 0
  for (let i = 0; i < 14; i++) {
    const v = chars.indexOf(g[i])
    const w = i % 2 === 0 ? v : v * 2
    sum += Math.floor(w / 36) + (w % 36)
  }
  const check = chars[(36 - (sum % 36)) % 36]
  if (check !== g[14]) return { ok: false, msg: 'Checksum failed. GSTIN may have a typo.' }
  const state = g.slice(0, 2)
  return { ok: true, msg: `Valid GSTIN. State code ${state}. Supplier exists in registry (mock).` }
}

export default function StockCheck() {
  const [fields, setFields] = useState({ open: '', buy: '', close: '', margin: '12', upi: '' })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [gstin, setGstin] = useState('')
  const [gstResult, setGstResult] = useState(null)

  function set(name, val) {
    setFields(f => ({ ...f, [name]: val }))
  }

  function loadDemo(idx) {
    const d = DEMOS[idx]
    setFields({ open: d.open, buy: d.buy, close: d.close, margin: d.margin, upi: d.upi })
    setResult(null); setError('')
  }

  function runCheck(e) {
    e.preventDefault()
    const { open, buy, close, margin, upi } = fields
    if ([open, buy, close, margin, upi].some(v => v === '' || isNaN(Number(v)))) {
      setError('Please fill all fields with numbers.'); return
    }
    setError('')
    const o = Number(open), b = Number(buy), c = Number(close), m = Number(margin), u = Number(upi)
    const cogs = o + b - c
    const implied = cogs * (1 + m / 100)
    const ratio = u / implied
    const delta = u - implied

    let verdict, cls, comment
    if (ratio >= 0.9 && ratio <= 1.1) {
      verdict = 'Match'; cls = 'match'
      comment = 'Sales and stock figures agree within 10%. This shop looks consistent.'
    } else if (ratio >= 0.75 && ratio < 0.9) {
      verdict = 'Under Review'; cls = 'review'
      comment = 'UPI inflow is below implied revenue. Could be cash sales not on UPI, or a stock overcount.'
    } else if (ratio > 1.1) {
      verdict = 'Under Review'; cls = 'review'
      comment = 'UPI inflow exceeds implied revenue. Could be advance payments or transfers not related to sales.'
    } else {
      verdict = 'Mismatch'; cls = 'mismatch'
      comment = 'Large gap between sales and stock. Needs manual review before proceeding.'
    }
    setResult({ implied, cogs, delta, ratio, verdict, cls, comment })
  }

  function checkGSTIN(e) {
    e.preventDefault()
    setGstResult(validateGSTIN(gstin.trim().toUpperCase()))
  }

  return (
    <section className="block" id="check">
      <h2>Check a shop's stock</h2>
      <p className="sub">Enter one month of figures in rupees, or load a demo shop.</p>

      <div className="grid2">
        <form className="sheet" onSubmit={runCheck} noValidate>
          <div className="demo">
            <button type="button" className="btn small" onClick={() => loadDemo(0)}>Load Lakshmi</button>
            <button type="button" className="btn small" onClick={() => loadDemo(1)}>Load Sri Ganesh</button>
          </div>
          {[
            ['open', 'Opening stock'],
            ['buy', 'Purchases this month'],
            ['close', 'Closing stock'],
            ['margin', 'Typical margin (%)'],
            ['upi', 'UPI inflow received'],
          ].map(([name, label]) => (
            <label key={name}>{label}
              <input type="number" name={name} min="0"
                value={fields[name]}
                onChange={e => set(name, e.target.value)}
                required />
            </label>
          ))}
          {error && <p className="err">{error}</p>}
          <button className="btn green" type="submit">Run the check</button>
        </form>

        <div className="sheet" aria-live="polite">
          {!result
            ? <p className="note">The result appears here.</p>
            : <>
                <table className="rows">
                  <tbody>
                    <tr><td>Cost of goods sold</td><td>{fmt(result.cogs)}</td></tr>
                    <tr><td>Implied revenue</td><td>{fmt(result.implied)}</td></tr>
                    <tr><td>UPI inflow</td><td>{fmt(Number(fields.upi))}</td></tr>
                    <tr><td>Delta</td>
                      <td className={result.delta >= 0 ? 'c-match' : 'c-mismatch'}>
                        {result.delta >= 0 ? '+' : ''}{fmt(result.delta)}
                      </td>
                    </tr>
                    <tr><td>Ratio</td><td>{(result.ratio * 100).toFixed(1)}%</td></tr>
                  </tbody>
                </table>
                <div className="verdict">
                  <p style={{ fontSize: 13, color: 'var(--sec)', maxWidth: '28ch', margin: 0 }}>{result.comment}</p>
                  <span className={`stamp ${result.cls}`}>{result.verdict}</span>
                </div>
              </>
          }
        </div>
      </div>

      <form className="sheet gst" onSubmit={checkGSTIN} noValidate>
        <label>Supplier GSTIN
          <input id="gstin" maxLength={15} placeholder="Example: 27AAPFU0939F1ZV"
            value={gstin} onChange={e => setGstin(e.target.value)} autoComplete="off" />
        </label>
        <button className="btn green" type="submit">Check GSTIN</button>
        {gstResult && (
          <p id="gst-out" style={{ color: gstResult.ok ? 'var(--ok)' : 'var(--bad)' }}>
            {gstResult.msg}
          </p>
        )}
      </form>
    </section>
  )
}
