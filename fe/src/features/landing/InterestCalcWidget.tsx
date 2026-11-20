import { useState } from 'react'
import { emi, totalInterest } from '../../engine/emi'
import { RangeField } from '../../components/ui/Field'
import Sheet from '../../components/ui/Sheet'
import LedgerTable from '../../components/ui/LedgerTable'

function fmt(n: number) {
  return '₹' + Math.round(n).toLocaleString('en-IN')
}

export default function InterestCalcWidget() {
  const [amt, setAmt] = useState(200_000)
  const [mon, setMon] = useState(18)
  const [r1, setR1] = useState(16)
  const [r2, setR2] = useState(36)

  const i1 = totalInterest(amt, r1, mon)
  const i2 = totalInterest(amt, r2, mon)
  const diff = i2 - i1

  return (
    <Sheet as="article">
      <h3>What it costs in interest</h3>
      <p className="note">Move the sliders. Rates are illustrative, not quotes.</p>

      <RangeField
        label="Loan amount"
        min={50_000}
        max={1_000_000}
        step={10_000}
        value={amt}
        format={fmt}
        onChange={(e) => setAmt(Number(e.target.value))}
      />
      <RangeField
        label="Months to repay"
        min={6}
        max={36}
        step={1}
        value={mon}
        format={(v) => String(v)}
        onChange={(e) => setMon(Number(e.target.value))}
      />
      <RangeField
        label="Bank rate, verified shop"
        min={9}
        max={24}
        step={0.5}
        value={r1}
        format={(v) => v + '%'}
        onChange={(e) => setR1(Number(e.target.value))}
      />
      <RangeField
        label="Informal lender rate"
        min={24}
        max={60}
        step={1}
        value={r2}
        format={(v) => v + '%'}
        onChange={(e) => setR2(Number(e.target.value))}
      />

      <LedgerTable
        rows={[
          { label: 'Bank loan', value: fmt(i1) },
          { label: 'Informal lender', value: fmt(i2) },
          {
            label: 'Extra paid for having no record',
            value: fmt(diff),
            total: true,
          },
        ]}
      />
    </Sheet>
  )
}
