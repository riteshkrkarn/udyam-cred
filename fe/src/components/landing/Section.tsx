import type { ReactNode } from "react";

export default function Section({
  id,
  title,
  intro,
  children,
}: {
  id?: string;
  title: string;
  intro?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="mx-auto max-w-6xl scroll-mt-24 px-6 py-14 md:px-10 md:py-20">
      <h2 className="max-w-3xl font-display text-3xl leading-tight text-ink md:text-4xl">
        {title}
      </h2>
      {intro && <p className="mt-4 max-w-2xl text-lg leading-8 text-moss">{intro}</p>}
      <div className="mt-10">{children}</div>
    </section>
  );
}
