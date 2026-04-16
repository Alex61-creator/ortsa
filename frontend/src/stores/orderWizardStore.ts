import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import { DEFAULT_REPORT_OPTIONS, type ReportOptionKey } from '@/constants/reportOptions'

interface OrderWizardState {
  tariffCode: string | null
  /** Для одиночных тарифов — один ID. Для bundle — первый из списка. */
  natalDataId: number | null
  /** Для тарифа bundle: все выбранные профили (1–3). */
  natalDataIds: number[]
  /** Доп. разделы отчёта (report / bundle), сохраняется между визитами визарда. */
  reportOptions: Record<ReportOptionKey, boolean>
  setTariffCode: (code: string | null) => void
  setNatalDataId: (id: number | null) => void
  setNatalDataIds: (ids: number[]) => void
  setReportOption: (key: ReportOptionKey, value: boolean) => void
  reset: () => void
}

export const useOrderWizardStore = create<OrderWizardState>()(
  persist(
    (set) => ({
      tariffCode: null,
      natalDataId: null,
      natalDataIds: [],
      reportOptions: { ...DEFAULT_REPORT_OPTIONS },
      setTariffCode: (tariffCode) => set({ tariffCode }),
      setNatalDataId: (natalDataId) => set({ natalDataId }),
      setNatalDataIds: (natalDataIds) =>
        set({ natalDataIds, natalDataId: natalDataIds[0] ?? null }),
      setReportOption: (key, value) =>
        set((s) => ({
          reportOptions: {
            ...DEFAULT_REPORT_OPTIONS,
            ...s.reportOptions,
            [key]: value,
          },
        })),
      reset: () =>
        set({
          tariffCode: null,
          natalDataId: null,
          natalDataIds: [],
          reportOptions: { ...DEFAULT_REPORT_OPTIONS },
        }),
    }),
    {
      name: 'astrogen_order_wizard',
      partialize: (s) => ({
        tariffCode: s.tariffCode,
        natalDataId: s.natalDataId,
        natalDataIds: s.natalDataIds,
        reportOptions: s.reportOptions,
      }),
      merge: (persisted, current) => {
        const p = (persisted ?? {}) as Partial<OrderWizardState>
        return {
          ...current,
          ...p,
          reportOptions: {
            ...DEFAULT_REPORT_OPTIONS,
            ...(p.reportOptions ?? {}),
          },
        }
      },
    }
  )
)
