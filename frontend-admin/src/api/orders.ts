import { api } from '@/api/client'
import type { AdminOrderRow, RefundResponse, RetryReportResponse } from '@/types/admin'

export interface OrdersListParams {
  page?: number
  page_size?: number
  status?: string
  user_id?: number
  q?: string
}

export async function fetchOrders(params: OrdersListParams): Promise<AdminOrderRow[]> {
  const { data } = await api.get<AdminOrderRow[]>('/api/v1/admin/orders', { params })
  return data
}

export async function fetchOrder(orderId: number): Promise<AdminOrderRow> {
  const { data } = await api.get<AdminOrderRow>(`/api/v1/admin/orders/${orderId}`)
  return data
}

export async function postRetryReport(orderId: number): Promise<RetryReportResponse> {
  const { data } = await api.post<RetryReportResponse>(
    `/api/v1/admin/orders/${orderId}/retry-report`
  )
  return data
}

export async function postRefund(orderId: number, amount?: string): Promise<RefundResponse> {
  const { data } = await api.post<RefundResponse>(
    `/api/v1/admin/orders/${orderId}/refund`,
    null,
    {
      params: amount ? { amount } : {},
    }
  )
  return data
}
