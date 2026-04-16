import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { OrdersPage } from '@/pages/OrdersPage'

vi.mock('@/api/orders', () => {
  const ORDER_ROW = {
    id: 1,
    user_id: 1,
    status: 'paid',
    amount: '100.00',
    natal_data_id: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    tariff: { code: 'report', name: 'Отчёт', billing_type: 'one_time', subscription_interval: null },
    report_ready: true,
  } as const

  const TIMELINE_ROWS = [
    {
      type: 'analytics',
      time: new Date().toISOString(),
      event_name: 'order_completed',
    },
  ]

  return {
    fetchOrders: vi.fn().mockResolvedValue([ORDER_ROW]),
    fetchOrder: vi.fn().mockResolvedValue(ORDER_ROW),
    fetchOrderTimeline: vi.fn().mockResolvedValue(TIMELINE_ROWS),
    postRefund: vi.fn(),
    postRetryReport: vi.fn(),
  }
})
vi.mock('@/api/reports', () => ({
  downloadOrderPdf: vi.fn(),
  downloadOrderChart: vi.fn(),
}))

describe('OrdersPage', () => {
  it('renders orders table', async () => {
    render(<OrdersPage />)
    await waitFor(() => expect(screen.getByText('Отчёт')).toBeInTheDocument())
  })

  it('renders order timeline in drawer', async () => {
    render(<OrdersPage />)
    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument())

    fireEvent.click(screen.getByText('#1'))

    await waitFor(() => expect(screen.getByText('Timeline')).toBeInTheDocument())
    expect(screen.getByText('order_completed')).toBeInTheDocument()
  })
})
