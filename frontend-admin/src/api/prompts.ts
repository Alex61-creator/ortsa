import { api } from '@/api/client'

export interface PromptTemplate {
  tariff_code: string
  locale: string
  system_prompt: string
  is_custom: boolean
  updated_at: string | null
  updated_by: string | null
}

export async function listPrompts(): Promise<PromptTemplate[]> {
  const { data } = await api.get<PromptTemplate[]>('/api/v1/admin/prompts/')
  return data
}

export async function getPrompt(tariffCode: string, locale: string): Promise<PromptTemplate> {
  const { data } = await api.get<PromptTemplate>(`/api/v1/admin/prompts/${tariffCode}/${locale}`)
  return data
}

export async function savePrompt(
  tariffCode: string,
  locale: string,
  systemPrompt: string,
): Promise<PromptTemplate> {
  const { data } = await api.put<PromptTemplate>(`/api/v1/admin/prompts/${tariffCode}/${locale}`, {
    system_prompt: systemPrompt,
  })
  return data
}

export async function resetPrompt(tariffCode: string, locale: string): Promise<void> {
  await api.delete(`/api/v1/admin/prompts/${tariffCode}/${locale}`)
}
