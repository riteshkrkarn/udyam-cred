/**
 * React Query hooks for API calls.
 * Wraps the client layer with loading/error state management.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  auth,
  reconciliation,
  bank,
  applications,
  setTokens,
  clearTokens,
  getRefreshToken,
  type LoginRequest,
  type RegisterRequest,
  type ShopReconcileRequest,
  type BankQueueResponse,
  type BankCaseResponse,
  type BankDecisionResponse,
  type ApplicationOut,
  ApiError,
} from './client'

// ============ Auth queries ============

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: auth.health,
  })
}

export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: auth.register,
    onSuccess: (user) => {
      qc.setQueryData(['user'], user)
    },
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: LoginRequest) => auth.login(req),
    onSuccess: (response) => {
      setTokens(response.access_token, response.refresh_token)
      qc.setQueryData(['auth', 'token'], response)
      // Refetch whoami to populate the current user
      qc.invalidateQueries({ queryKey: ['auth', 'whoami'] })
    },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const rt = getRefreshToken()
      if (!rt) return { revoked: false }
      return auth.logout(rt)
    },
    onSuccess: () => {
      clearTokens()
      qc.clear()
    },
  })
}

export function useRefresh() {
  return useMutation({
    mutationFn: async () => {
      const rt = getRefreshToken()
      if (!rt) throw new Error('No refresh token')
      return auth.refresh({ refresh_token: rt })
    },
    onSuccess: (response) => {
      setTokens(response.access_token, response.refresh_token)
    },
  })
}

export function useWhoami() {
  return useQuery({
    queryKey: ['auth', 'whoami'],
    queryFn: auth.whoami,
    retry: false,
    enabled: !!getRefreshToken(), // only run if we have a token
  })
}

// ============ Reconciliation queries ============

export function useReconcile() {
  return useMutation({
    mutationFn: (shop: ShopReconcileRequest) => reconciliation.check(shop),
  })
}

// Prefetch reconcile result (for optimistic UI)
export function usePrefetchReconcile() {
  const qc = useQueryClient()
  return (shop: ShopReconcileRequest) => {
    qc.prefetchQuery({
      queryKey: ['reconcile', shop.shop_id],
      queryFn: () => reconciliation.check(shop),
    })
  }
}

// ============ Bank / Officer queries ============

export function useBankQueue(params?: { status?: string; skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['bank', 'queue', params],
    queryFn: () => bank.queue(params),
  })
}

export function useBankCase(appId: string | number | undefined) {
  return useQuery({
    queryKey: ['bank', 'case', appId],
    queryFn: () => bank.caseDetail(appId!),
    enabled: !!appId,
  })
}

export function useBankDecision(appId: string | number | undefined) {
  return useQuery({
    queryKey: ['bank', 'decision', appId],
    queryFn: () => bank.decision(appId!),
    enabled: !!appId,
  })
}

export function useBankOverride() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ appId, reason, newAmount }: { appId: string | number; reason: string; newAmount?: number }) =>
      bank.override(appId, reason, newAmount),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['bank', 'queue'] })
      qc.invalidateQueries({ queryKey: ['bank', 'case', vars.appId] })
    },
  })
}

export function useApplications(status?: string) {
  return useQuery({
    queryKey: ['applications', status],
    queryFn: () => applications.list(status),
  })
}

export function useApplication(id: number | string | undefined) {
  return useQuery({
    queryKey: ['applications', id],
    queryFn: () => applications.get(id!),
    enabled: !!id,
  })
}

export function useCreateApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { shop_id?: number; loan_amount_requested: number; purpose: string }) =>
      applications.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['applications'] })
    },
  })
}
