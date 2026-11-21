import Section from "./Section";

const STEPS = [
  {
    title: "Apply and give consent",
    body: "Tell us the amount and the purpose, then choose what data we may read.",
  },
  {
    title: "Link your bank data",
    body: "Share bank statements through Account Aggregator, and your GST filings if you are registered.",
  },
  {
    title: "Photograph the shop",
    body: "A few photos: shop front, shelves and your rent receipt, with our code written on paper in view.",
  },
  {
    title: "We compare the sources",
    body: "Bank, GST and UPI sales are checked against each other. Only months where bank data overlaps with GST or UPI count as verified.",
  },
  {
    title: "You get a tier, an amount and a plan",
    body: "Plain reasons for the result, the repayment schedule, when each part of the loan is released, and what to do to reach the next tier.",
  },
];

export default function HowItWorks() {
  return (
    <Section
      id="how"
      title="How a shop gets its loan"
      intro="No audited accounts and no collateral. The shop brings consent and a few photos, and the records do the rest."
    >
      <ol className="max-w-3xl border-t border-rule">
        {STEPS.map((s, i) => (
          <li key={s.title} className="grid grid-cols-[3rem_1fr] gap-4 border-b border-rule py-5">
            <span className="font-display text-3xl text-wine tabular-nums">{i + 1}</span>
            <div>
              <h3 className="text-lg font-semibold text-ink">{s.title}</h3>
              <p className="mt-1 text-base leading-7 text-moss">{s.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </Section>
  );
}
