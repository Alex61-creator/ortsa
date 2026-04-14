import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { OrdersPage } from '@/pages/OrdersPage'

vi.mock('@/api/orders', () => ({
  fetchOrders: vi.fn().mockResolvedValue([
    {
      id: 1,
      user_id: 1,
      status: 'paid',
      amount: '100.00',
      natal_data_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      tariff: { code: 'report', name: 'Отчёт', billing_type: 'one_time', subscription_interval: null },
      report_ready: true,
    },
  ]),
  fetchOrder: vi.fn(),
  postRefund: vi.fn(),
  postRetryReport: vi.fn(),
}))
vi.mock('@/api/reports', () => ({
  downloadOrderPdf: vi.fn(),
  downloadOrderChart: vi.fn(),
}))

describe('OrdersPage', () => {
  it('renders orders table', async () => {
    render(<OrdersPage />)
    await waitFor(() => expect(screen.getByText('Отчёт')).toBeInTheDocument())
  })
})
