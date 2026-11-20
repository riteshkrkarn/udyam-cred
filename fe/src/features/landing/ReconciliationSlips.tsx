import { SEED_SHOPS } from '../../data/seedShops'
import { reconcile } from '../../engine/reconcile'
import Sheet from '../../components/ui/Sheet'
import LedgerTable from '../../components/ui/LedgerTable'
import Stamp from '../../components/ui/Stamp'

function fmt(n: number) {
  return '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN')
}

function ShopSlip({ shop }: { shop: (typeof SEED_SHOPS)[0] }) {
  const r = reconcile({
    openingStock: shop.openingStock,
    purchases: shop.purchases,
    closingStock: shop.closingStock,
    marginPct: shop.marginPct,
    upiInflow: shop.upiInflow,
  })

  const deltaLabel =
    r.delta >= 0 ? `+${fmt(r.delta)} surplus` : `${fmt(r.delta)} shortfall`
  const deltaClass = r.delta >= 0 ? 'c-match' : 'c-mismatch'

  return (
    <Sheet as="article">
      <div className="slip-head">
        <div>
          <h3>{shop.name}</h3>
          <p className="note" style={{ margin: 0 }}>
            One-month reconciliation slip
          </p>
        </div>
        <span className="folio">{shop.id}</span>
      </div>

      <LedgerTable
        rows={[
          { label: 'Opening stock', value: fmt(shop.openingStock) },
          { label: 'Purchases', value: fmt(shop.purchases) },
          { label: 'Closing stock', value: fmt(shop.closingStock) },
          { label: 'Cost of goods sold', value: fmt(r.cogs), highlight: true },
          { label: `Margin applied (${shop.marginPct}%)`, value: '' },
          { label: 'Implied revenue', value: fmt(r.impliedRevenue), total: true },
          { label: 'UPI inflow received', value: fmt(shop.upiInflow) },
        ]}
      />

      <div className="verdict">
        <div>
          <span className={deltaClass} style={{ fontWeight: 600, fontSize: 14 }}>
            {deltaLabel}
          </span>
          <i style={{ display: 'block' }}>{(r.ratio * 100).toFixed(0)}% of implied revenue</i>
        </div>
        <Stamp verdict={r.verdict} />
      </div>
    </Sheet>
  )
}

export default function ReconciliationSlips() {
  return (
    <>
      {SEED_SHOPS.map((shop) => (
        <ShopSlip key={shop.id} shop={shop} />
      ))}
    </>
  )
}
