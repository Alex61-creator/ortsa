import { api } from '@/api/client'
import type { OrderCreatePayload, OrderListItem, OrderOut } from '@/types/api'

export async function listOrders(): Promise<OrderListItem[]> {
  const { data } = await api.get<OrderListItem[]>('/orders/')
  return data
}

export async function getOrder(orderId: number): Promise<OrderListItem> {
  const { data } = await api.get<OrderListItem>(`/orders/${orderId}`)
  return data
}

export async function createOrder(payload: OrderCreatePayload): Promise<OrderOut> {
  const { data } = await api.post<OrderOut>('/orders/', payload)
  return data
}

export async function retryOrderPayment(orderId: number): Promise<OrderOut> {
  const { data } = await api.post<OrderOut>(`/orders/${orderId}/retry-payment`)
  return data
}
