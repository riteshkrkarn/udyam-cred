import Section from "./Section";

const ITEMS = [
  {
    title: "Queue by tier",
    body: "Pending applications are counted and sorted by tier, so officers see where the work is.",
  },
  {
    title: "Case view with every source",
    body: "Bank, GST and UPI sales side by side, how closely they agree, the photo checks, and the plain reasons for the tier.",
  },
  {
    title: "Replay",
    body: "Change an input, for example verified months from 10 to 5, and watch the tier and amount move. The saved decision is not touched.",
  },
  {
    title: "Override with a reason",
    body: "An officer can overrule the result but must write why. The reason is stored with the decision.",
  },
  {
    title: "Audit trail",
    body: "Applications, consent, scoring, tier, releases, repayments, overrides and freezes are all logged with who did them and when.",
  },
];

export default function OfficerSection() {
  return (
    <Section
      id="officers"
      title="Built for the officer who has to sign the decision"
      intro="UdyamCred gives decision support. It shows its working so the officer can check it, change it or overrule it."
    >
      <ul className="grid gap-x-10 gap-y-6 md:grid-cols-2">
        {ITEMS.map((i) => (
          <li key={i.title} className="border-t border-rule pt-4">
            <h3 className="text-lg font-semibold text-ink">{i.title}</h3>
            <p className="mt-1 text-base leading-7 text-moss">{i.body}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
