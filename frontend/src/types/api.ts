export type OrderStatus =
  | 'pending'
  | 'failed_to_init_payment'
  | 'paid'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'refunded'
  | 'canceled'

export interface UserMe {
  id: number
  email: string
  is_admin: boolean
  created_at: string
  consent_given_at: string | null
  oauth_provider: string | null
}

export interface TariffPublic {
  code: string
  name: string
  price: string
  /** Display USD for EN landing; billing uses `price` (RUB). */
  price_usd?: string | null
  compare_price_usd?: string | null
  annual_total_usd?: string | null
  features: Record<string, unknown>
  retention_days: number
  priority: number
}

export interface NatalDataOut {
  id: number
  user_id: number
  full_name: string
  birth_date: string
  birth_time: string
  birth_place: string
  lat: number
  lon: number
  timezone: string
  house_system: string
  report_locale: 'ru' | 'en'
  created_at: string
}

export interface NatalDataCreatePayload {
  full_name: string
  birth_date: string
  birth_time: string
  birth_place: string
  lat: number
  lon: number
  timezone: string
  house_system: string
  accept_privacy_policy: boolean
  /** Язык PDF и письма: ru | en */
  report_locale?: 'ru' | 'en'
}

export interface NatalDataUpdatePayload {
  full_name?: string
  birth_place?: string
  lat?: number
  lon?: number
  timezone?: string
  house_system?: string
  report_locale?: 'ru' | 'en'
}

export interface OrderListItem {
  id: number
  status: OrderStatus
  amount: string
  natal_data_id: number | null
  created_at: string
  updated_at: string
  tariff: {
    code: string
    name: string
    billing_type: string
    subscription_interval: string | null
  }
  report_ready: boolean
}

export interface OrderCreatePayload {
  tariff_code: string
  natal_data_id: number
}

export interface OrderOut {
  id: number
  user_id: number
  natal_data_id: number | null
  tariff_id: number
  status: string
  amount: string
  yookassa_id: string | null
  confirmation_url: string | null
  created_at: string
}

export interface TwAuthResponse {
  access_token: string
  token_type: string
}
