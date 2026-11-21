import { useState } from "react";
import { TIERS, tierRate, RATES_NOTE, type TierId } from "@/lib/landing-content";
import { emi, inr } from "@/lib/finance";

export default function CostCompare() {
  const [tierId, setTierId] = useState<TierId>(1);
  const [amount, setAmount] = useState(40000);
  const [months, setMonths] = useState(12);
  const [informal, setInformal] = useState(36);

  const tier = TIERS.find((t) => t.id === tierId)!;
  const amt = Math.min(amount, tier.maxAmount);
  const mon = Math.min(months, tier.tenureMonths);
  const rate = tierRate(tier.id);

  const oursEmi = emi(amt, rate, mon);
  const theirEmi = emi(amt, informal, mon);
  const oursInterest = oursEmi * mon - amt;
  const theirInterest = theirEmi * mon - amt;
  const saved = theirInterest - oursInterest;

  const amountStep = tier.maxAmount >= 1000000 ? 25000 : 5000;

  return (
    <div className="rounded-sm border border-rule bg-paper p-6 shadow-sm">
      <h2 className="font-display text-2xl text-ink">What it costs in interest</h2>
      <hr className="my-4 border-rule" />
      <p className="text-sm text-moss">
        Pick a tier, then move the sliders. Rates are illustrative, not quotes.
      </p>

      <div role="radiogroup" aria-label="Loan tier" className="mt-4 flex gap-2">
        {TIERS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="radio"
            aria-checked={t.id === tierId}
            onClick={() => setTierId(t.id)}
            className={
              "flex-1 rounded-sm border px-3 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-wine " +
              (t.id === tierId
                ? "border-pine bg-pine text-paper"
                : "border-rule bg-sage text-ink hover:border-pine")
            }
          >
            {t.name}
          </button>
        ))}
      </div>

      <Slider
        id="amount"
        label="Loan amount"
        value={amt}
        display={inr(amt)}
        min={10000}
        max={tier.maxAmount}
        step={amountStep}
        onChange={setAmount}
      />
      <Slider
        id="months"
        label="Months to repay"
        value={mon}
        display={String(mon)}
        min={6}
        max={tier.tenureMonths}
        step={1}
        onChange={setMonths}
      />
      <Slider
        id="informal"
        label="Informal lender rate you were quoted"
        value={informal}
        display={`${informal}%`}
        min={24}
        max={60}
        step={1}
        onChange={setInformal}
      />

      <div className="overflow-x-auto">
        <table className="mt-6 w-full text-left text-sm">
          <caption className="sr-only">Cost comparison</caption>
          <thead>
            <tr className="border-b border-rule text-moss">
              <th className="py-2 font-normal" scope="col"></th>
              <th className="py-2 font-semibold text-ink" scope="col">{tier.name}</th>
              <th className="py-2 font-semibold text-ink" scope="col">Informal</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            <tr className="border-b border-rule">
              <th className="py-2 font-normal text-moss" scope="row">Yearly rate</th>
              <td>{rate.toFixed(1)}%</td>
              <td>{informal}%</td>
            </tr>
            <tr className="border-b border-rule">
              <th className="py-2 font-normal text-moss" scope="row">Monthly EMI</th>
              <td>{inr(oursEmi)}</td>
              <td>{inr(theirEmi)}</td>
            </tr>
            <tr>
              <th className="py-2 font-normal text-moss" scope="row">Total interest</th>
              <td>{inr(oursInterest)}</td>
              <td>{inr(theirInterest)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-base text-ink" aria-live="polite">
        {saved > 0
          ? `At ${tier.name}, the shop keeps ${inr(saved)} more over ${mon} months.`
          : "At this informal rate there is no saving. Lower the rate you were quoted to compare."}
      </p>
      <p className="mt-3 text-xs leading-5 text-moss">
        Both columns use the same reducing-balance sum. Informal lenders often quote flat or
        daily charges, so enter the rate that matches your own quote. Amounts are capped at
        what the tier allows. {RATES_NOTE}
      </p>
    </div>
  );
}

function Slider(props: {
  id: string;
  label: string;
  value: number;
  display: string;
  min: number;
  max: number;
  step: number;
  onChange: (n: number) => void;
}) {
  const { id, label, value, display, min, max, step, onChange } = props;
  return (
    <div className="mt-5">
      <div className="flex items-baseline justify-between text-sm text-ink">
        <label htmlFor={id}>{label}</label>
        <output htmlFor={id} className="tabular-nums">{display}</output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-wine"
      />
    </div>
  );
}
