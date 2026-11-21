export default function MissedChances() {
  return (
    <div className="rounded-sm border border-rule bg-paper p-6 shadow-sm">
      <h2 className="font-display text-2xl text-ink">What it costs in missed chances</h2>
      <hr className="my-4 border-rule" />
      <p className="text-sm text-moss">Money the shop could have put to work.</p>
      <ul className="mt-4 space-y-3 text-base text-ink">
        <li className="flex gap-3"><Dot />Cannot stock up before a festival, when sales are highest.</li>
        <li className="flex gap-3"><Dot />Cannot buy in bulk from suppliers.</li>
        <li className="flex gap-3"><Dot />Shelving, a fridge or a new product line stay on hold.</li>
      </ul>
      <hr className="my-5 border-rule" />
      <p className="text-xs leading-5 text-moss">
        Small businesses go without about ₹30 lakh crore of credit, roughly 24% of what they
        ask for. For women-owned shops the gap is 35%. Source: SIDBI and Crisil MSME Pulse, 2025.
      </p>
    </div>
  );
}

const Dot = () => <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-wine" />;
