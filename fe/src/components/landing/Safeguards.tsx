import Section from "./Section";
import { TIERS } from "@/lib/landing-content";

const SEG = ["bg-pine", "bg-wine", "bg-ochre", "bg-moss"];

export default function Safeguards() {
  return (
    <Section
      id="safeguards"
      title="Money is released in parts, and only while repayments stay on time"
      intro="Larger loans are paid out in stages. The next part is released only if every earlier EMI was paid on time."
    >
      <div className="grid gap-8 md:grid-cols-5">
        <div className="space-y-6 md:col-span-3">
          {TIERS.map((t) => (
            <div key={t.id}>
              <p className="text-sm font-semibold text-ink">{t.name}</p>
              <div
                role="img"
                aria-label={`${t.name} payout: ${t.tranches
                  .map((s, i) => `${Math.round(s * 100)} percent on day ${t.trancheDays[i]}`)
                  .join(", ")}`}
                className="mt-2 flex h-9 overflow-hidden rounded-sm"
              >
                {t.tranches.map((s, i) => (
                  <div
                    key={i}
                    style={{ width: `${s * 100}%` }}
                    className={`flex items-center justify-center text-xs tabular-nums text-paper ${SEG[i]}`}
                  >
                    {Math.round(s * 100)}%
                  </div>
                ))}
              </div>
              <p className="mt-1 text-xs text-moss">
                {t.tranches.length === 1
                  ? "Paid on day 0."
                  : `Paid on day ${t.trancheDays.join(", ")}. Each later part waits for on-time EMIs.`}
              </p>
            </div>
          ))}
        </div>

        <aside className="rounded-sm border border-ochre bg-ochre-tint p-6 md:col-span-2">
          <h3 className="font-display text-xl text-ink">If payments are missed</h3>
          <dl className="mt-4 space-y-4 text-sm leading-6 text-ink">
            <div>
              <dt className="font-semibold">One missed EMI</dt>
              <dd>You get a late notice.</dd>
            </div>
            <div>
              <dt className="font-semibold">Two missed EMIs</dt>
              <dd>
                Remaining parts of the loan are frozen and an officer reviews the case. The
                officer can unfreeze it and must record a note.
              </dd>
            </div>
          </dl>
        </aside>
      </div>
    </Section>
  );
}
