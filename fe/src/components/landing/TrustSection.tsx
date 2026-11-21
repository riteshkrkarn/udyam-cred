import Section from "./Section";
import { TRUSTED_SOURCES, CROSS_CHECK_ONLY } from "@/lib/landing-content";

const BAR = ["bg-pine", "bg-wine", "bg-ochre"];

export default function TrustSection() {
  return (
    <Section
      id="trust"
      title="We lend on records the owner cannot edit"
      intro="A purchase bill can be written to suit a loan. A bank statement shared by the bank cannot. So the second kind of record carries the decision, and the first kind only helps us cross-check."
    >
      <div className="grid gap-8 md:grid-cols-5">
        <div className="rounded-sm border border-rule bg-paper p-6 shadow-sm md:col-span-3">
          <h3 className="font-display text-xl text-ink">Sources we count</h3>
          <p className="mt-2 text-sm text-moss">
            When all three are available, monthly sales are weighted like this. If one is
            missing, the others carry the weight and our confidence falls.
          </p>

          <div
            role="img"
            aria-label="Weights: bank data 60 percent, GST 30 percent, UPI 10 percent"
            className="mt-5 flex h-4 w-full overflow-hidden rounded-sm"
          >
            {TRUSTED_SOURCES.map((s, i) => (
              <div key={s.name} style={{ width: `${s.weight}%` }} className={BAR[i]} />
            ))}
          </div>

          <ul className="mt-6 divide-y divide-rule">
            {TRUSTED_SOURCES.map((s, i) => (
              <li key={s.name} className="flex gap-4 py-3">
                <span aria-hidden className={`mt-1.5 h-3 w-3 shrink-0 rounded-sm ${BAR[i]}`} />
                <div>
                  <p className="text-base text-ink">
                    {s.name} <span className="tabular-nums text-moss">({s.weight}%)</span>
                  </p>
                  <p className="text-sm text-moss">{s.note}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-8 md:col-span-2">
          <div className="rounded-sm border border-rule bg-paper p-6 shadow-sm">
            <h3 className="font-display text-xl text-ink">The shop photo</h3>
            <p className="mt-2 text-sm leading-6 text-moss">
              You photograph the shop with a code we give you written on paper. We read the
              code, check that the photo is recent, and compare its location with your rent
              address, within 500 metres.
            </p>
          </div>
          <div className="rounded-sm border border-rule bg-paper p-6 shadow-sm">
            <h3 className="font-display text-xl text-ink">Cross-check only</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-moss">
              {CROSS_CHECK_ONLY.map((c) => <li key={c}>{c}</li>)}
            </ul>
            <p className="mt-3 text-sm leading-6 text-moss">
              These help us see whether the records agree. They never approve a loan on their own.
            </p>
          </div>
        </div>
      </div>
    </Section>
  );
}
