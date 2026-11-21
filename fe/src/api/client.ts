/**
 * API client for the UdyamCred backend.
 * Handles token management, error responses, and base URL configuration.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface HealthResponse {
  status: string
  version: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserResponse {
  id: number
  email: string
  role: string
}

export interface RegisterRequest {
  email: string
  password: string
  role: 'borrower' | 'officer' | 'approver' | 'auditor'
}

export interface LoginRequest {
  email: string
  password: string
  remember_me?: boolean
}

export interface RefreshRequest {
  refresh_token: string
}

export interface ShopReconcileRequest {
  shop_id: number
  gstin: string
  shop_category: string
  purchases: number
  gst_turnover: number
  upi_turnover: number
  inventory_value?: number
  cash_sales?: number
}

export interface ReconcileResponse {
  shop_id: number | null
  gstin_valid: boolean
  shop_category: string
  margin_low: number
  margin_high: number
  goods_sold: number
  expected_sales_low: number
  expected_sales_high: number
  reported_sales: number
  upi_turnover: number
  gst_turnover: number
  verdict: string
  reason: string
}

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail)
    this.name = 'ApiError'
  }
}

export { ApiError }

// Token management
let accessToken: string | null = null
let refreshToken: string | null = null

export function setTokens(access: string, refresh: string) {
  accessToken = access
  refreshToken = refresh
  localStorage.setItem('udyam_access_token', access)
  localStorage.setItem('udyam_refresh_token', refresh)
}

export function getAccessToken(): string | null {
  return accessToken || localStorage.getItem('udyam_access_token')
}

export function getRefreshToken(): string | null {
  return refreshToken || localStorage.getItem('udyam_refresh_token')
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
  localStorage.removeItem('udyam_access_token')
  localStorage.removeItem('udyam_refresh_token')
}

// Request helper
async function request<T>(
  endpoint: string,
  init?: RequestInit & { useAuth?: boolean },
): Promise<T> {
  const { useAuth = true, ...options } = init || {}

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (options.headers) {
    const headerEntries = options.headers instanceof Headers 
      ? Array.from(options.headers.entries())
      : Object.entries(options.headers as Record<string, string>)
    headerEntries.forEach(([key, value]) => {
      headers[key] = String(value)
    })
  }

  if (useAuth) {
    const token = getAccessToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
  }

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      // couldn't parse error response
    }
    throw new ApiError(res.status, detail)
  }

  return res.json() as Promise<T>
}

// Auth endpoints
export const auth = {
  health: () => request<HealthResponse>('/health', { useAuth: false }),

  register: (req: RegisterRequest) =>
    request<UserResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(req),
      useAuth: false,
    }),

  login: (req: LoginRequest) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(req),
      useAuth: false,
    }),

  refresh: (req: RefreshRequest) =>
    request<TokenResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify(req),
      useAuth: false,
    }),

  logout: (refreshToken: string) =>
    request<{ revoked: boolean }>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      useAuth: false,
    }),

  whoami: () => request<UserResponse>('/shops/me'),
}

// Reconciliation endpoint
export const reconciliation = {
  check: (shop: ShopReconcileRequest) =>
    request<ReconcileResponse>('/reconcile', {
      method: 'POST',
      body: JSON.stringify(shop),
    }),
}

// ── Bank / Officer endpoints ──────────────────────────────────────────────────

export interface BankQueueResponse {
  total: number
  applications: {
    id: number
    shop_id: number | null
    amount_requested: number | null
    status: string
    created_at: string
  }[]
}

export interface BankCaseResponse {
  application_id: number
  tier: number
  amount: number
  confidence: number
  status: string
  photos_count: number
  documents_count: number
  bank_inflows_months: number
}

export interface BankDecisionResponse {
  tier: number
  amount: number
  tenor_months: number
  rate_percent: number
  reasons: string[]
  tranche_plan: Record<string, { amount: number; condition: string }>
}

export const bank = {
  queue: (params?: { status?: string; skip?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.skip !== undefined) qs.set('skip', String(params.skip))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<BankQueueResponse>(`/bank/queue${qs.toString() ? '?' + qs : ''}`)
  },

  caseDetail: (appId: string | number) =>
    request<BankCaseResponse>(`/bank/cases/${appId}`),

  decision: (appId: string | number) =>
    request<BankDecisionResponse>(`/bank/cases/${appId}/decision`),

  override: (appId: string | number, reason: string, newAmount?: number) => {
    const qs = new URLSearchParams({ reason })
    if (newAmount !== undefined) qs.set('new_amount', String(newAmount))
    return request<{ status: string; application_id: number }>(
      `/bank/cases/${appId}/override?${qs}`,
      { method: 'POST' },
    )
  },

  auditLog: (params?: { skip?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.skip !== undefined) qs.set('skip', String(params.skip))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<{ entries: unknown[]; total: number }>(`/bank/audit${qs.toString() ? '?' + qs : ''}`)
  },
}

// ── Applications endpoints ────────────────────────────────────────────────────

export interface ApplicationOut {
  id: number
  borrower_id: number | null
  shop_id: number | null
  loan_amount_requested: number
  purpose: string
  status: string
  created_at: string
}

export const applications = {
  list: (status?: string) => {
    const qs = status ? `?status=${status}` : ''
    return request<ApplicationOut[]>(`/api/applications${qs}`)
  },
  get: (id: number | string) => request<ApplicationOut>(`/api/applications/${id}`),
  create: (body: { shop_id?: number; loan_amount_requested: number; purpose: string }) =>
    request<ApplicationOut>('/api/applications', { method: 'POST', body: JSON.stringify(body) }),
  updateStatus: (id: number | string, status: string) =>
    request<ApplicationOut>(`/api/applications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
}
