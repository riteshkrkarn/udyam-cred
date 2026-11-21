import Section from "./Section";
import { GLOSSARY } from "@/lib/landing-content";

export default function Glossary() {
  return (
    <Section id="glossary" title="Words we use, in plain language">
      <div className="max-w-3xl border-t border-rule">
        {GLOSSARY.map((g) => (
          <details key={g.term} className="group border-b border-rule py-3">
            <summary className="cursor-pointer list-none text-base font-semibold text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-wine">
              {g.term}
            </summary>
            <p className="mt-2 text-base leading-7 text-moss">{g.meaning}</p>
          </details>
        ))}
      </div>
    </Section>
  );
}
