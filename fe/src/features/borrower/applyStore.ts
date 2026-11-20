import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type LoanPurpose =
  | 'Stock purchase'
  | 'Festival stock'
  | 'Shop expansion'
  | 'Working capital'
  | 'Other'

export interface ApplyFormValues {
  amount: number
  purpose: LoanPurpose | ''
  consent: boolean
}

interface ApplyState {
  draft: Partial<ApplyFormValues>
  submitted: boolean
  applicationId: string | null
  saveDraft: (values: Partial<ApplyFormValues>) => void
  submit: (values: ApplyFormValues) => string
  reset: () => void
}

function generateId() {
  return 'UC-' + new Date().getFullYear() + '-' + String(Math.floor(Math.random() * 9000) + 1000)
}

export const useApplyStore = create<ApplyState>()(
  persist(
    (set) => ({
      draft: {},
      submitted: false,
      applicationId: null,
      saveDraft: (values) => set((s) => ({ draft: { ...s.draft, ...values } })),
      submit: (values) => {
        const id = generateId()
        set({ draft: values, submitted: true, applicationId: id })
        return id
      },
      reset: () => set({ draft: {}, submitted: false, applicationId: null }),
    }),
    { name: 'udyamcred-apply' },
  ),
)
