/**
 * useTierAssignment: Custom hook for fetching and managing tier assignment logic
 * Handles tier determination, rules, and next-tier criteria
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'

export interface TierAssignmentData {
  tier: number
  max_amount: number
  rate_adjustment: number
  tranche_plan: 'single' | '2-3' | '4+'
  tenure_months: number
  reasons: string[]
  next_tier_criteria: string[]
}

export interface TierRules {
  tier: number
  name: string
  min_verified_months: number
  min_amount: number
  max_amount: number
  rate_adjustment: number
  confidence_threshold: number
  requires_gst: boolean
  requires_udyam: boolean
}

/**
 * Fetch tier assignment for an application
 */
export function useTierAssignment(applicationId: string | null) {
  return useQuery({
    queryKey: ['tier-assignment', applicationId],
    queryFn: async () => {
      if (!applicationId) throw new Error('Application ID required')

      const response = await fetch(`/api/applications/${applicationId}/tier`)
      if (!response.ok) throw new Error('Failed to fetch tier assignment')
      return response.json() as Promise<TierAssignmentData>
    },
    enabled: !!applicationId,
  })
}

/**
 * Fetch all tier rules/definitions
 */
export function useTierRules() {
  return useQuery({
    queryKey: ['tier-rules'],
    queryFn: async () => {
      const response = await fetch('/api/tiers')
      if (!response.ok) throw new Error('Failed to fetch tier rules')
      return response.json() as Promise<TierRules[]>
    },
    staleTime: 1000 * 60 * 60, // 1 hour
  })
}

/**
 * Check eligibility for next tier
 */
export function useTierEligibility(applicationId: string | null, currentTier: number) {
  const [nextTierCriteria, setNextTierCriteria] = useState<string[]>([])
  const [isEligible, setIsEligible] = useState(false)

  useEffect(() => {
    if (!applicationId || currentTier >= 3) {
      setIsEligible(false)
      setNextTierCriteria([])
      return
    }

    async function checkEligibility() {
      try {
        const response = await fetch(
          `/api/applications/${applicationId}/tier-eligibility?target_tier=${currentTier + 1}`
        )
        if (response.ok) {
          const data = await response.json()
          setIsEligible(data.eligible)
          setNextTierCriteria(data.missing_criteria || [])
        }
      } catch (error) {
        console.error('Failed to check tier eligibility:', error)
      }
    }

    checkEligibility()
  }, [applicationId, currentTier])

  return { isEligible, nextTierCriteria }
}

/**
 * Tier names and descriptions
 */
export const TIER_INFO = {
  1: {
    name: 'Tier 1',
    description: 'Quick loans for emerging businesses',
    minAmount: 10000,
    maxAmount: 50000,
    tenor: 12,
    rate: '+4%',
    tranches: 1,
    icon: '🌱',
  },
  2: {
    name: 'Tier 2',
    description: 'Mid-size loans for established GST-registered businesses',
    minAmount: 50000,
    maxAmount: 250000,
    tenor: 24,
    rate: '+2%',
    tranches: '2-3',
    icon: '📈',
  },
  3: {
    name: 'Tier 3',
    description: 'Large loans for Udyam-registered businesses with repayment history',
    minAmount: 250000,
    maxAmount: 1000000,
    tenor: 36,
    rate: '+0%',
    tranches: '4+',
    icon: '🏢',
  },
}

/**
 * Get tier color for UI
 */
export function getTierColor(tier: number): string {
  const colors = {
    1: '#90EE90', // Light green
    2: '#87CEEB', // Sky blue
    3: '#DDA0DD', // Plum
  }
  return colors[tier as keyof typeof colors] || '#ccc'
}

/**
 * Get tier badge
 */
export function getTierBadge(tier: number): React.ReactNode {
  const info = TIER_INFO[tier as keyof typeof TIER_INFO]
  if (!info) return null
  return `${info.icon} ${info.name}`
}

/**
 * Format tier requirements for display
 */
export function formatTierRequirements(tier: number): string[] {
  const requirements: { [key: number]: string[] } = {
    1: [
      '6+ months verified bank data',
      'Sales sources agree (>70%)',
      'Shop location verified with photos',
      'No GST registration required',
    ],
    2: [
      '12+ months verified bank data',
      'GST registration required',
      'Sales sources agree (>80%)',
      'Shop location verified',
    ],
    3: [
      '24+ months verified bank data',
      'GST registration required',
      'Udyam registration required',
      'Prior on-time repayment history',
      'Sales sources agree (>85%)',
    ],
  }
  return requirements[tier] || []
}

/**
 * Format tier benefits for display
 */
export function formatTierBenefits(tier: number): string[] {
  const benefits: { [key: number]: string[] } = {
    1: [
      'Up to ₹50,000 loan',
      '12-month tenure',
      'Single tranche (full amount at once)',
      'Fast approval (24 hours)',
    ],
    2: [
      'Up to ₹2,50,000 loan',
      '24-month tenure',
      '2-3 tranches (staged releases)',
      'Lower interest rate',
      'Access after 6 months on-time repayment from Tier 1',
    ],
    3: [
      'Up to ₹10,00,000 loan',
      '36-month tenure',
      '4+ tranches (gradual releases)',
      'Lowest interest rate',
      'Requires prior successful loan history',
    ],
  }
  return benefits[tier] || []
}
