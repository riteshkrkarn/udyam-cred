export function emi(principal: number, annualRatePct: number, months: number): number {
  const r = annualRatePct / 12 / 100;
  if (r === 0) return principal / months;
  return (principal * r) / (1 - Math.pow(1 + r, -months));
}

export const inr = (n: number): string =>
  "₹" + Math.round(n).toLocaleString("en-IN");
