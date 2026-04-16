/** Канонические ключи доп. разделов отчёта (совпадают с бэкендом). */
export const REPORT_OPTION_KEYS = [
  'partnership',
  'children_parenting',
  'career',
  'money_boundaries',
] as const

export type ReportOptionKey = (typeof REPORT_OPTION_KEYS)[number]

export const DEFAULT_REPORT_OPTIONS: Record<ReportOptionKey, boolean> = {
  partnership: false,
  children_parenting: false,
  career: false,
  money_boundaries: false,
}

export function isReportUpsellTariff(tariffCode: string | null): boolean {
  return tariffCode === 'report' || tariffCode === 'bundle'
}

/** Только включённые ключи — для POST /orders/. */
export function buildReportOptionsPayload(
  flags: Record<ReportOptionKey, boolean>
): Record<string, boolean> | undefined {
  const out: Record<string, boolean> = {}
  for (const k of REPORT_OPTION_KEYS) {
    if (flags[k]) out[k] = true
  }
  return Object.keys(out).length ? out : undefined
}

/**
 * Превью строки «тумблеры» (как на сервере: сумма цен из API, multi-скидка при 2+).
 */
export function computeToggleLinePreview(
  selected: Record<ReportOptionKey, boolean>,
  priceByKey: Record<string, number>,
  multiDiscountPercent: number
): number {
  const keys = REPORT_OPTION_KEYS.filter((k) => selected[k])
  if (keys.length === 0) return 0

  let raw = 0
  for (const k of keys) {
    const p = priceByKey[k]
    if (p != null && !Number.isNaN(p) && p >= 0) {
      raw += Math.round(p * 100) / 100
    }
  }

  if (keys.length >= 2 && multiDiscountPercent > 0) {
    raw *= (100 - multiDiscountPercent) / 100
  }
  return Math.round(raw * 100) / 100
}
