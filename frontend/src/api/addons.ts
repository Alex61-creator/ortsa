import { api } from './client'

export interface AddonOffer {
  addon_code: string
  title: string
  description?: string | null
  price: string
  currency: string
  eligible: boolean
  eligibility_reasons: string[]
  parent_order_id: number | null
  offer_expires_at: string | null
}

export interface AddonPurchaseOut {
  payment_url: string
  addon_order_id: number
  status: string
}

export async function listAddons(): Promise<AddonOffer[]> {
  const { data } = await api.get<AddonOffer[]>('/addons')
  return data
}

export async function purchaseAddon(addonCode: string): Promise<AddonPurchaseOut> {
  const { data } = await api.post<AddonPurchaseOut>(`/addons/${addonCode}/purchase`)
  return data
}
