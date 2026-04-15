import { api } from './client'

export interface SynastryOut {
  id: number
  natal_data_id_1: number
  natal_data_id_2: number
  person1_name: string | null
  person2_name: string | null
  status: 'pending' | 'processing' | 'completed' | 'failed'
  locale: string
  generation_count: number
  last_generated_at: string | null
  next_regen_allowed_at: string | null
  pdf_ready: boolean
  created_at: string
  updated_at: string
}

export interface SynastryQuota {
  tariff_code: string
  pairs_used: number
  pairs_max: number
  has_access: boolean
}

export interface SynastryCreatePayload {
  natal_data_id_1: number
  natal_data_id_2: number
  locale?: 'ru' | 'en'
}

export async function listSynastry(): Promise<SynastryOut[]> {
  const { data } = await api.get<SynastryOut[]>('/synastry')
  return data
}

export async function getSynastry(id: number): Promise<SynastryOut> {
  const { data } = await api.get<SynastryOut>(`/synastry/${id}`)
  return data
}

export async function getSynastryQuota(): Promise<SynastryQuota> {
  const { data } = await api.get<SynastryQuota>('/synastry/quota')
  return data
}

export async function createSynastry(payload: SynastryCreatePayload): Promise<SynastryOut> {
  const { data } = await api.post<SynastryOut>('/synastry', payload)
  return data
}

export async function regenerateSynastry(id: number): Promise<SynastryOut> {
  const { data } = await api.post<SynastryOut>(`/synastry/${id}/regenerate`)
  return data
}

export async function deleteSynastry(id: number): Promise<void> {
  await api.delete(`/synastry/${id}`)
}

import { getApiBaseUrl } from './client'

export function getSynastryDownloadUrl(id: number): string {
  return `${getApiBaseUrl()}/synastry/${id}/download`
}
