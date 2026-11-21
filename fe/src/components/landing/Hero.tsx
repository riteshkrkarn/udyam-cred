import { Link } from "react-router-dom";

export default function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-6 pb-10 pt-14 md:px-10">
      <div className="border-l-4 border-double border-wine pl-6 md:pl-8">
        <p className="text-sm tracking-wide text-moss">
          Verification-first lending for small shops
        </p>
        <h1 className="mt-3 max-w-4xl font-display text-4xl leading-[1.1] text-ink md:text-6xl">
          No credit score. The shop still leaves proof, and we read it.
        </h1>
        <p className="mt-8 max-w-2xl text-lg leading-8 text-moss">
          UdyamCred lends only against records the owner cannot edit: bank data shared
          through Account Aggregator, GST filings, UPI records and a geo-tagged photo of
          the shop. The more history a shop has verified, the higher it climbs, from a
          first loan of up to ₹50,000 to as much as ₹10,00,000.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/apply"
            className="rounded-sm bg-wine px-5 py-3 text-sm font-semibold text-paper hover:bg-wine-deep focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-wine"
          >
            Apply for a loan
          </Link>
          <a
            href="#trust"
            className="rounded-sm bg-pine px-5 py-3 text-sm font-semibold text-paper hover:bg-pine-deep focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine"
          >
            Check a shop
          </a>
        </div>
        <p className="mt-5 text-sm text-moss">
          UdyamCred supports the loan officer. The officer makes the final decision.
        </p>
      </div>
    </section>
  );
}
