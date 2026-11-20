// Shared formatting helpers
export function fmt(n) {
  return '₹' + Math.round(n).toLocaleString('en-IN')
}

export function emi(principal, annualRate, months) {
  const r = annualRate / 100 / 12
  if (r === 0) return principal / months
  return (principal * r * Math.pow(1 + r, months)) / (Math.pow(1 + r, months) - 1)
}

export function totalInterest(principal, annualRate, months) {
  return emi(principal, annualRate, months) * months - principal
}
