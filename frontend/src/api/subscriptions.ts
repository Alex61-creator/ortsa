import { api } from '@/api/client'

export interface SubscriptionOut {
  id: number
  tariff_code: string
  tariff_name: string
  status: string
  amount: string
  current_period_start: string | null
  current_period_end: string | null
  cancel_at_period_end: boolean
  status_message: string | null
}

export async function fetchMySubscription(): Promise<SubscriptionOut | null> {
  const { data } = await api.get<SubscriptionOut | null>('/subscriptions/me')
  return data
}

export async function cancelMySubscription(): Promise<SubscriptionOut> {
  const { data } = await api.post<SubscriptionOut>('/subscriptions/me/cancel')
  return data
}

export async function resumeMySubscription(): Promise<SubscriptionOut> {
  const { data } = await api.post<SubscriptionOut>('/subscriptions/me/resume')
  return data
}
