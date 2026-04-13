import { api } from '@/api/client'

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}

export async function downloadOrderPdf(orderId: number): Promise<void> {
  const { data } = await api.get<Blob>(`/api/v1/admin/reports/orders/${orderId}/pdf`, {
    responseType: 'blob',
  })
  triggerBlobDownload(data, `natal_report_${orderId}.pdf`)
}

export async function downloadOrderChart(orderId: number): Promise<void> {
  const { data } = await api.get<Blob>(`/api/v1/admin/reports/orders/${orderId}/chart`, {
    responseType: 'blob',
  })
  triggerBlobDownload(data, `natal_chart_${orderId}.png`)
}
