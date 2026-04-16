/** Коды тарифов подписки (совпадает с app/constants/tariffs.SUBSCRIPTION_CODES). */
const SUBSCRIPTION_CODES = new Set(['sub_monthly', 'sub_annual'])

export function isSubscriptionTariffCode(code: string | null | undefined): boolean {
  if (!code) return false
  return SUBSCRIPTION_CODES.has(code.toLowerCase())
}
