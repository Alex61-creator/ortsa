import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface OrderWizardState {
  tariffCode: string | null
  /** Для одиночных тарифов — один ID. Для bundle — первый из списка. */
  natalDataId: number | null
  /** Для тарифа bundle: все выбранные профили (1–3). */
  natalDataIds: number[]
  setTariffCode: (code: string | null) => void
  setNatalDataId: (id: number | null) => void
  setNatalDataIds: (ids: number[]) => void
  reset: () => void
}

export const useOrderWizardStore = create<OrderWizardState>()(
  persist(
    (set) => ({
      tariffCode: null,
      natalDataId: null,
      natalDataIds: [],
      setTariffCode: (tariffCode) => set({ tariffCode }),
      setNatalDataId: (natalDataId) => set({ natalDataId }),
      setNatalDataIds: (natalDataIds) =>
        set({ natalDataIds, natalDataId: natalDataIds[0] ?? null }),
      reset: () => set({ tariffCode: null, natalDataId: null, natalDataIds: [] }),
    }),
    {
      name: 'astrogen_order_wizard',
      partialize: (s) => ({
        tariffCode: s.tariffCode,
        natalDataId: s.natalDataId,
        natalDataIds: s.natalDataIds,
      }),
    }
  )
)
