import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Role = 'borrower' | 'officer' | 'approver' | 'auditor' | null

interface User {
  id: number
  email: string
  role: Role
}

interface AuthState {
  user: User | null
  demoRole: Role // For offline demo mode
  useDemo: boolean
  isAuthenticated: boolean
  setUser: (user: User | null) => void
  setDemoRole: (role: Role) => void
  setUseDemo: (use: boolean) => void
  signOut: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      demoRole: null,
      useDemo: true, // Start in demo mode (no backend required)
      isAuthenticated: false,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
          useDemo: false,
        }),

      setDemoRole: (role) => set({ demoRole: role, useDemo: true }),

      setUseDemo: (use) => set({ useDemo: use }),

      signOut: () =>
        set({
          user: null,
          demoRole: null,
          useDemo: true,
          isAuthenticated: false,
        }),
    }),
    { name: 'udyamcred-auth' },
  ),
)

/**
 * Get the current role, preferring real user role over demo role.
 */
export function getCurrentRole(state: AuthState): Role {
  if (state.user) return state.user.role
  if (state.useDemo) return state.demoRole
  return null
}
