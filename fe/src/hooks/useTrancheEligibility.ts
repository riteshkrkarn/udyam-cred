/**
 * useTrancheEligibility: Custom hook for checking multi-tranche release eligibility
 * Verifies EMI payment status before releasing next tranche
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'

export interface TrancheInfo {
  tranche_num: number
  amount: number
  release_date: string
  status: 'pending' | 'released' | 'repaid'
  emi_count: number
  tenor_months: number
}

export interface TrancheEligibility {
  tranche_num: number
  eligible: boolean
  reason: string
  required_on_time_emis: number
  current_on_time_emis: number
  release_date_if_eligible: string
}

export interface RepaymentRecord {
  emi_num: number
  due_date: string
  amount: number
  paid_date?: string
  status: 'pending' | 'ontime' | 'late' | 'missed' | 'bounced'
  days_late?: number
}

/**
 * Fetch all tranches for an application
 */
export function useTranches(applicationId: string | null) {
  return useQuery({
    queryKey: ['tranches', applicationId],
    queryFn: async () => {
      if (!applicationId) throw new Error('Application ID required')

      const response = await fetch(`/api/applications/${applicationId}/tranches`)
      if (!response.ok) throw new Error('Failed to fetch tranches')
      return response.json() as Promise<TrancheInfo[]>
    },
    enabled: !!applicationId,
  })
}

/**
 * Check eligibility for a specific tranche
 */
export function useTrancheEligibilityCheck(
  applicationId: string | null,
  trancheNum: number
) {
  return useQuery({
    queryKey: ['tranche-eligibility', applicationId, trancheNum],
    queryFn: async () => {
      if (!applicationId) throw new Error('Application ID required')

      const response = await fetch(
        `/api/applications/${applicationId}/tranches/${trancheNum}/eligibility`
      )
      if (!response.ok) throw new Error('Failed to check eligibility')
      return response.json() as Promise<TrancheEligibility>
    },
    enabled: !!applicationId && trancheNum > 0,
  })
}

/**
 * Fetch repayment history for an application
 */
export function useRepaymentHistory(applicationId: string | null) {
  return useQuery({
    queryKey: ['repayment-history', applicationId],
    queryFn: async () => {
      if (!applicationId) throw new Error('Application ID required')

      const response = await fetch(`/api/applications/${applicationId}/repayment`)
      if (!response.ok) throw new Error('Failed to fetch repayment history')
      const data = await response.json()
      return data.emi_schedule as Promise<RepaymentRecord[]>
    },
    enabled: !!applicationId,
  })
}

/**
 * Check next EMI due
 */
export function useNextEMIDue(applicationId: string | null) {
  const [nextEMI, setNextEMI] = useState<RepaymentRecord | null>(null)
  const [daysUntilDue, setDaysUntilDue] = useState<number | null>(null)

  const { data: repaymentHistory } = useRepaymentHistory(applicationId)

  useEffect(() => {
    if (repaymentHistory) {
      const pending = repaymentHistory.find(r => r.status === 'pending')
      if (pending) {
        setNextEMI(pending)
        const dueDate = new Date(pending.due_date)
        const today = new Date()
        const diffTime = dueDate.getTime() - today.getTime()
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        setDaysUntilDue(diffDays)
      } else {
        setNextEMI(null)
        setDaysUntilDue(null)
      }
    }
  }, [repaymentHistory])

  return { nextEMI, daysUntilDue }
}

/**
 * Calculate repayment status for dashboard/summary
 */
export function useRepaymentStatus(applicationId: string | null) {
  const [status, setStatus] = useState({
    totalEMIs: 0,
    onTimeEMIs: 0,
    lateEMIs: 0,
    missedEMIs: 0,
    bouncedEMIs: 0,
    onTimePercent: 0,
    isAccountFrozen: false,
  })

  const { data: repaymentHistory } = useRepaymentHistory(applicationId)

  useEffect(() => {
    if (repaymentHistory && repaymentHistory.length > 0) {
      const totalEMIs = repaymentHistory.length
      const onTimeEMIs = repaymentHistory.filter(r => r.status === 'ontime').length
      const lateEMIs = repaymentHistory.filter(r => r.status === 'late').length
      const missedEMIs = repaymentHistory.filter(r => r.status === 'missed').length
      const bouncedEMIs = repaymentHistory.filter(r => r.status === 'bounced').length

      // Account is frozen if 2+ EMIs are missed/bounced
      const isFrozen = missedEMIs + bouncedEMIs >= 2

      setStatus({
        totalEMIs,
        onTimeEMIs,
        lateEMIs,
        missedEMIs,
        bouncedEMIs,
        onTimePercent: (onTimeEMIs / totalEMIs) * 100,
        isAccountFrozen: isFrozen,
      })
    }
  }, [repaymentHistory])

  return status
}

/**
 * Format tranche status with icon
 */
export function formatTrancheStatus(
  status: 'pending' | 'released' | 'repaid'
): { label: string; icon: string; color: string } {
  const statuses = {
    pending: { label: 'Pending', icon: '⏳', color: '#FFA500' },
    released: { label: 'Released', icon: '✓', color: '#90EE90' },
    repaid: { label: 'Repaid', icon: '✅', color: '#228B22' },
  }
  return statuses[status]
}

/**
 * Format EMI status with icon
 */
export function formatEMIStatus(
  status: 'pending' | 'ontime' | 'late' | 'missed' | 'bounced'
): { label: string; icon: string; color: string } {
  const statuses = {
    pending: { label: 'Pending', icon: '⏳', color: '#FFA500' },
    ontime: { label: 'On Time', icon: '✓', color: '#90EE90' },
    late: { label: 'Late', icon: '⚠', color: '#FF8C00' },
    missed: { label: 'Missed', icon: '✗', color: '#FF6B6B' },
    bounced: { label: 'Bounced', icon: '⚠⚠', color: '#DC143C' },
  }
  return statuses[status]
}

/**
 * Determine if tranche should be eligible for release
 * Rule: All EMIs from previous tranches must be on-time
 */
export function isTranchesEligible(
  trancheNum: number,
  repaymentHistory: RepaymentRecord[] | undefined
): boolean {
  if (!repaymentHistory || trancheNum === 1) return true

  // For now, check if there are any missed/bounced EMIs
  // In real implementation, check only EMIs belonging to previous tranches
  const hasFailedEMI = repaymentHistory.some(r =>
    ['missed', 'bounced'].includes(r.status)
  )
  return !hasFailedEMI
}

/**
 * Get tranche release schedule description
 */
export function getTrancheReleaseSchedule(
  trancheNum: number,
  totalTranches: number,
  amount: number
): string {
  if (totalTranches === 1) {
    return `Full ₹${amount.toLocaleString()} released now`
  }

  const percentages = {
    1: 0.6, // 60%
    2: 0.4, // 40%
    3: 0.3, // 30% (for 4+ tranches)
    4: 0.1, // 10% (for 4+ tranches)
  }

  let schedule = `Tranche ${trancheNum} of ${totalTranches}: `

  if (totalTranches === 2) {
    if (trancheNum === 1) {
      schedule += `₹${Math.round(amount * 0.6).toLocaleString()} now`
    } else {
      schedule += `₹${Math.round(amount * 0.4).toLocaleString()} at +60 days`
    }
  } else if (totalTranches === 3) {
    if (trancheNum === 1) {
      schedule += `₹${Math.round(amount * 0.5).toLocaleString()} now`
    } else if (trancheNum === 2) {
      schedule += `₹${Math.round(amount * 0.3).toLocaleString()} at +60 days`
    } else {
      schedule += `₹${Math.round(amount * 0.2).toLocaleString()} at +120 days`
    }
  } else {
    // 4+ tranches
    const pct = percentages[trancheNum as keyof typeof percentages] || 0.1
    schedule += `₹${Math.round(amount * pct).toLocaleString()} at +${(trancheNum - 1) * 60} days`
  }

  return schedule
}
