import Section from "./Section";
import { TIERS, INDUSTRY_RATES, tierRate, RATES_NOTE } from "@/lib/landing-content";
import { inr } from "@/lib/finance";

const OFFSET = ["md:mt-20", "md:mt-10", "md:mt-0"];

export default function TierLadder() {
  return (
    <Section
      id="tiers"
      title="Three tiers. Each one is earned with verified history."
      intro="A shop starts where its verified records place it, and moves up as the record grows. The rate is the industry rate for the tier plus a small adjustment that falls as trust grows."
    >
      <div className="grid items-start gap-6 md:grid-cols-3">
        {TIERS.map((t, i) => (
          <article
            key={t.id}
            className={`rounded-sm border border-rule bg-paper p-6 shadow-sm ${OFFSET[i]}`}
          >
            <h3 className="font-display text-2xl text-ink">{t.name}</h3>
            <p className="mt-1 text-sm text-moss">{t.tagline}</p>

            <p className="mt-5 font-display text-4xl text-wine tabular-nums">
              Up to {inr(t.maxAmount)}
            </p>
            <dl className="mt-4 space-y-2 text-sm">
              <Row k="Repay over" v={`up to ${t.tenureMonths} months`} />
              <Row k="Paid out" v={t.tranches.length === 1 ? "In one go" : `In ${t.tranches.length} parts`} />
              <Row
                k="Rate"
                v={`Industry rate + ${t.adjustment}%`}
              />
              <Row
                k="At illustrative rates"
                v={`${INDUSTRY_RATES[t.id].toFixed(1)} + ${t.adjustment} = ${tierRate(t.id).toFixed(1)}%`}
              />
            </dl>

            <h4 className="mt-5 text-sm font-semibold text-ink">What the shop needs</h4>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-moss">
              {t.needs.map((n) => <li key={n}>{n}</li>)}
            </ul>

            <p className="mt-5 border-t border-rule pt-4 text-sm leading-6 text-ink">
              {t.nextStep ?? "This is the top tier. Keep repaying on time to keep it."}
            </p>
          </article>
        ))}
      </div>
      <p className="mt-8 max-w-2xl text-xs leading-5 text-moss">
        The amount you are offered is usually below the cap. It is scaled by how long your
        history has been verified and how closely your sources agree. {RATES_NOTE}
      </p>
    </Section>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-rule pb-2">
      <dt className="text-moss">{k}</dt>
      <dd className="text-right tabular-nums text-ink">{v}</dd>
    </div>
  );
}
