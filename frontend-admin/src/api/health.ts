import { api } from '@/api/client'
import type { HealthWidget } from '@/types/admin'

export async function fetchHealthWidgets() {
  const { data } = await api.get<HealthWidget[]>('/api/v1/admin/health/')
  return data
}
