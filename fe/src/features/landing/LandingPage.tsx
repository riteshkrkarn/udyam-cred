import Hero from "@/components/landing/Hero";
import CostCompare from "@/components/landing/CostCompare";
import MissedChances from "@/components/landing/MissedChances";
import TrustSection from "@/components/landing/TrustSection";
import HowItWorks from "@/components/landing/HowItWorks";
import TierLadder from "@/components/landing/TierLadder";
import Safeguards from "@/components/landing/Safeguards";
import WorkedExample from "@/components/landing/WorkedExample";
import OfficerSection from "@/components/landing/OfficerSection";
import Glossary from "@/components/landing/Glossary";

export default function LandingPage() {
  return (
    <>
      <Hero />
      <section className="mx-auto grid max-w-6xl gap-8 px-6 pb-6 md:grid-cols-2 md:px-10">
        <CostCompare />
        <MissedChances />
      </section>
      <TrustSection />
      <HowItWorks />
      <TierLadder />
      <Safeguards />
      <WorkedExample />
      <OfficerSection />
      <Glossary />
      <p className="mx-auto max-w-6xl px-6 pb-12 text-xs leading-5 text-moss md:px-10">
        This demo uses synthetic shops and mock bank, GST and UPI data. Rates are illustrative.
        UdyamCred supports the loan officer and does not replace them.
      </p>
    </>
  );
}
