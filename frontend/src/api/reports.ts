import { api } from '@/api/client'

export async function downloadReportPdf(orderId: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/reports/${orderId}/download`, {
    responseType: 'blob',
  })
  return data
}

export async function downloadReportChart(orderId: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/reports/${orderId}/chart`, {
    responseType: 'blob',
  })
  return data
}
