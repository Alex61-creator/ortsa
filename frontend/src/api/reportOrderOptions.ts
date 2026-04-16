import { api } from '@/api/client'
import type { ReportOrderOptionsOut } from '@/types/api'

export async function getReportOrderOptions(): Promise<ReportOrderOptionsOut> {
  const { data } = await api.get<ReportOrderOptionsOut>('/report-order-options/')
  return data
}
