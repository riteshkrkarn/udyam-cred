import { useState } from 'react'
import { reconcile, type ReconcileResult } from '../../engine/reconcile'
import { validateGSTIN } from '../../engine/gstin'
import Sheet from '../../components/ui/Sheet'
import LedgerTable from '../../components/ui/LedgerTable'
import Stamp from '../../components/ui/Stamp'
import { SEED_SHOPS } from '../../data/seedShops'

function fmt(n: number) {
  return '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN')
}

type Fields = {
  open: string
  buy: string
  close: string
  margin: string
  upi: string
}

const EMPTY: Fields = { open: '', buy: '', close: '', margin: '12', upi: '' }

export default function StockCheckSection() {
  const [fields, setFields] = useState<Fields>(EMPTY)
  const [result, setResult] = useState<ReconcileResult | null>(null)
  const [error, setError] = useState('')
  const [gstin, setGstin] = useState('')
  const [gstResult, setGstResult] = useState<{ ok: boolean; msg: string } | null>(null)

  function set(name: keyof Fields, val: string) {
    setFields((f) => ({ ...f, [name]: val }))
  }

  function loadDemo(idx: number) {
    const d = SEED_SHOPS[idx]
    setFields({
      open: String(d.openingStock),
      buy: String(d.purchases),
      close: String(d.closingStock),
      margin: String(d.marginPct),
      upi: String(d.upiInflow),
    })
    setResult(null)
    setError('')
  }

  function runCheck(e: React.FormEvent) {
    e.preventDefault()
    const nums = [fields.open, fields.buy, fields.close, fields.margin, fields.upi].map(Number)
    if (nums.some((v) => isNaN(v) || v === 0)) {
      setError('Please fill all fields with numbers.')
      return
    }
    setError('')
    setResult(
      reconcile({
        openingStock: nums[0],
        purchases: nums[1],
        closingStock: nums[2],
        marginPct: nums[3],
        upiInflow: nums[4],
      }),
    )
  }

  function checkGSTIN(e: React.FormEvent) {
    e.preventDefault()
    setGstResult(validateGSTIN(gstin))
  }

  return (
    <section className="block" id="check">
      <h2>Check a shop's stock</h2>
      <p className="sub">Enter one month of figures in rupees, or load a demo shop.</p>

      <div className="grid2">
        <form className="sheet" onSubmit={runCheck} noValidate>
          <div className="demo">
            <button type="button" className="btn small" onClick={() => loadDemo(0)}>
              Load Lakshmi
            </button>
            <button type="button" className="btn small" onClick={() => loadDemo(1)}>
              Load Sri Ganesh
            </button>
          </div>
          {(
            [
              ['open', 'Opening stock'],
              ['buy', 'Purchases this month'],
              ['close', 'Closing stock'],
              ['margin', 'Typical margin (%)'],
              ['upi', 'UPI inflow received'],
            ] as [keyof Fields, string][]
          ).map(([name, lbl]) => (
            <label key={name}>
              {lbl}
              <input
                type="number"
                name={name}
                min="0"
                value={fields[name]}
                onChange={(e) => set(name, e.target.value)}
                required
              />
            </label>
          ))}
          {error && <p className="err">{error}</p>}
          <button className="btn green" type="submit">
            Run the check
          </button>
        </form>

        <Sheet ariaLive="polite">
          {!result ? (
            <p className="note">The result appears here.</p>
          ) : (
            <>
              <LedgerTable
                rows={[
                  { label: 'Cost of goods sold', value: fmt(result.cogs) },
                  { label: 'Implied revenue', value: fmt(result.impliedRevenue) },
                  { label: 'UPI inflow', value: fmt(Number(fields.upi)) },
                  {
                    label: 'Delta',
                    value: (result.delta >= 0 ? '+' : '') + fmt(result.delta),
                  },
                  { label: 'Ratio', value: (result.ratio * 100).toFixed(1) + '%' },
                ]}
              />
              <div className="verdict">
                <p
                  style={{
                    fontSize: 13,
                    color: 'var(--sec)',
                    maxWidth: '28ch',
                    margin: 0,
                  }}
                >
                  {result.comment}
                </p>
                <Stamp verdict={result.verdict} />
              </div>
            </>
          )}
        </Sheet>
      </div>

      <form className="sheet gst" onSubmit={checkGSTIN} noValidate>
        <label>
          Supplier GSTIN
          <input
            id="gstin"
            maxLength={15}
            placeholder="Example: 27AAPFU0939F1ZV"
            value={gstin}
            onChange={(e) => setGstin(e.target.value)}
            autoComplete="off"
          />
        </label>
        <button className="btn green" type="submit">
          Check GSTIN
        </button>
        {gstResult && (
          <p id="gst-out" style={{ color: gstResult.ok ? 'var(--ok)' : 'var(--bad)', marginTop: '0.8rem', fontSize: 14 }}>
            {gstResult.msg}
          </p>
        )}
      </form>
    </section>
  )
}
