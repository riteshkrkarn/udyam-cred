// Two synthetic demo shops: one reconciles cleanly, one does not.
const SHOPS = [
  {
    id: 'UC-2025-0041',
    name: 'Lakshmi Provision Store',
    open: 180000,
    buy: 420000,
    close: 95000,
    margin: 12,
    upi: 510000,
  },
  {
    id: 'UC-2025-0078',
    name: 'Sri Ganesh General Stores',
    open: 210000,
    buy: 380000,
    close: 145000,
    margin: 11,
    upi: 510000,
  },
]

function reconcile(shop) {
  const costOfGoodsSold = shop.open + shop.buy - shop.close
  const impliedRevenue = costOfGoodsSold * (1 + shop.margin / 100)
  const ratio = shop.upi / impliedRevenue
  const delta = shop.upi - impliedRevenue

  let verdict, cls
  if (ratio >= 0.9 && ratio <= 1.1) {
    verdict = 'Match'; cls = 'match'
  } else if (ratio >= 0.75 && ratio < 0.9) {
    verdict = 'Under Review'; cls = 'review'
  } else {
    verdict = 'Mismatch'; cls = 'mismatch'
  }
  return { impliedRevenue, delta, verdict, cls, ratio }
}

function fmt(n) {
  return '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN')
}

function Slip({ shop }) {
  const r = reconcile(shop)
  const deltaLabel = r.delta >= 0 ? `+${fmt(r.delta)} surplus` : `${fmt(r.delta)} shortfall`
  const deltaClass = r.delta >= 0 ? 'c-match' : 'c-mismatch'

  return (
    <article className="sheet">
      <div className="slip-head">
        <div>
          <h3>{shop.name}</h3>
          <p className="note" style={{ margin: 0 }}>One-month reconciliation slip</p>
        </div>
        <span className="folio">{shop.id}</span>
      </div>

      <table className="rows" style={{ marginTop: '1rem' }}>
        <tbody>
          <tr><td>Opening stock</td><td>{fmt(shop.open)}</td></tr>
          <tr><td>Purchases</td><td>{fmt(shop.buy)}</td></tr>
          <tr><td>Closing stock</td><td>{fmt(shop.close)}</td></tr>
          <tr className="hl"><td>Cost of goods sold</td><td>{fmt(shop.open + shop.buy - shop.close)}</td></tr>
          <tr><td>Margin applied ({shop.margin}%)</td><td></td></tr>
          <tr className="total"><td>Implied revenue</td><td>{fmt(r.impliedRevenue)}</td></tr>
          <tr><td>UPI inflow received</td><td>{fmt(shop.upi)}</td></tr>
        </tbody>
      </table>

      <div className="verdict">
        <div>
          <span className={deltaClass} style={{ fontWeight: 600, fontSize: 14 }}>{deltaLabel}</span>
          <i style={{ display: 'block' }}>{(r.ratio * 100).toFixed(0)}% of implied revenue</i>
        </div>
        <span className={`stamp ${r.cls}`}>{r.verdict}</span>
      </div>
    </article>
  )
}

export default function Slips() {
  return (
    <>
      {SHOPS.map(s => <Slip key={s.id} shop={s} />)}
    </>
  )
}
