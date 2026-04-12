import { create } from 'zustand'

interface OrderWizardState {
  tariffCode: string | null
  natalDataId: number | null
  setTariffCode: (code: string | null) => void
  setNatalDataId: (id: number | null) => void
  reset: () => void
}

export const useOrderWizardStore = create<OrderWizardState>((set) => ({
  tariffCode: null,
  natalDataId: null,
  setTariffCode: (tariffCode) => set({ tariffCode }),
  setNatalDataId: (natalDataId) => set({ natalDataId }),
  reset: () => set({ tariffCode: null, natalDataId: null }),
}))
