import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface OrderWizardState {
  tariffCode: string | null
  natalDataId: number | null
  setTariffCode: (code: string | null) => void
  setNatalDataId: (id: number | null) => void
  reset: () => void
}

export const useOrderWizardStore = create<OrderWizardState>()(
  persist(
    (set) => ({
      tariffCode: null,
      natalDataId: null,
      setTariffCode: (tariffCode) => set({ tariffCode }),
      setNatalDataId: (natalDataId) => set({ natalDataId }),
      reset: () => set({ tariffCode: null, natalDataId: null }),
    }),
    {
      name: 'astrogen_order_wizard',
      partialize: (s) => ({ tariffCode: s.tariffCode, natalDataId: s.natalDataId }),
    }
  )
)
