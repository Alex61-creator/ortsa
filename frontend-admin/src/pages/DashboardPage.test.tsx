import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { DashboardPage } from '@/pages/DashboardPage'

vi.mock('@/api/dashboard', () => ({
  fetchDashboardSummary: vi.fn().mockResolvedValue({
    order_metrics: { failed_orders_total: 1, processing_stuck_over_2h: 2, checked_at: new Date().toISOString() },
    analytics_stub: false,
    future_docs: '',
  }),
}))

describe('DashboardPage', () => {
  it('renders operational metrics', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      const label = screen.getByText('Failed заказов')
      const card = label.parentElement
      expect(card).not.toBeNull()
      expect(within(card as HTMLElement).getByText('1')).toBeInTheDocument()
    })
  })
})
