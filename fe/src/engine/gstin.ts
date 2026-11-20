/**
 * GSTIN format validator and checksum verifier.
 * Pattern: 2-digit state + 10-char PAN + entity num + Z + check digit.
 */

const CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

export interface GstinResult {
  ok: boolean
  stateCode?: string
  msg: string
}

export function validateGSTIN(raw: string): GstinResult {
  const g = raw.trim().toUpperCase()
  const pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/
  if (!pattern.test(g)) {
    return { ok: false, msg: 'Format invalid. Expected pattern: 27AAPFU0939F1ZV' }
  }

  // Luhn-style checksum over first 14 characters
  let sum = 0
  for (let i = 0; i < 14; i++) {
    const v = CHARS.indexOf(g[i])
    const w = i % 2 === 0 ? v : v * 2
    sum += Math.floor(w / 36) + (w % 36)
  }
  const expected = CHARS[(36 - (sum % 36)) % 36]
  if (expected !== g[14]) {
    return { ok: false, msg: 'Checksum failed — GSTIN may have a typo.' }
  }

  const stateCode = g.slice(0, 2)
  return {
    ok: true,
    stateCode,
    msg: `Valid GSTIN. State code ${stateCode}. Supplier exists in registry (mock).`,
  }
}
