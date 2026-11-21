import Section from "./Section";
import { TIERS, INDUSTRY_RATES, tierRate } from "@/lib/landing-content";
import { emi, inr } from "@/lib/finance";

const REASONS = [
  "Verified 10 months of bank data.",
  "Your bank and UPI records agree on sales by 82%.",
  "Shop location matches your rent address.",
  "Tier 1: a first loan for shops building a record.",
];
const NEXT = [
  "Register for GST to qualify for Tier 2.",
  "Keep up 6 or more months of on-time repayment.",
  "Grow verified history to 12 months.",
];

export default function WorkedExample() {
  const t = TIERS[0];
  const verifiedMonths = 10;
  const minMonths = 6;
  const agreement = 0.82;
  const verifiedWeight = Math.min(verifiedMonths / minMonths, 1);
  const amount = Math.round(t.maxAmount * verifiedWeight * agreement);
  const rate = tierRate(1);
  const monthly = emi(amount, rate, t.tenureMonths);

  return (
    <Section
      id="example"
      title="How one amount is worked out"
      intro="An illustrative Tier 1 shop. Every step can be read, and an officer can replay it with different inputs."
    >
      <div className="grid gap-8 md:grid-cols-2">
        <div className="rounded-sm border border-rule bg-paper p-6 shadow-sm">
          <h3 className="font-display text-xl text-ink">The sum</h3>
          <dl className="mt-4 space-y-3 text-sm tabular-nums">
            <Line k="Tier 1 cap" v={inr(t.maxAmount)} />
            <Line k={`Verified months (${verifiedMonths} of ${minMonths} needed)`} v={`x ${verifiedWeight.toFixed(2)}`} />
            <Line k="Sources agree" v={`x ${agreement.toFixed(2)}`} />
            <Line k="Approved amount" v={inr(amount)} strong />
            <Line k={`Rate (${INDUSTRY_RATES[1]} + ${t.adjustment})`} v={`${rate.toFixed(1)}%`} />
            <Line k={`EMI over ${t.tenureMonths} months`} v={inr(monthly)} strong />
          </dl>
        </div>

        <div className="rounded-sm border border-rule bg-paper p-6 shadow-sm">
          <h3 className="font-display text-xl text-ink">What the owner sees</h3>
          <p className="mt-3 text-sm font-semibold text-ink">Why this result</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm leading-6 text-moss">
            {REASONS.map((r) => <li key={r}>{r}</li>)}
          </ul>
          <p className="mt-4 text-sm font-semibold text-ink">How to reach the next tier</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm leading-6 text-moss">
            {NEXT.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      </div>
    </Section>
  );
}

function Line({ k, v, strong }: { k: string; v: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-4 border-b border-rule pb-2 ${strong ? "font-semibold text-ink" : "text-moss"}`}>
      <dt>{k}</dt>
      <dd className="text-ink">{v}</dd>
    </div>
  );
}
