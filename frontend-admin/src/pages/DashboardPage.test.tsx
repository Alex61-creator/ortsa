import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { DashboardPage } from '@/pages/DashboardPage'

vi.mock('@/api/dashboard', () => ({
  fetchDashboardSummary: vi.fn().mockResolvedValue({
    order_metrics: { failed_orders_total: 1, processing_stuck_over_2h: 2, checked_at: new Date().toISOString() },
    analytics_stub: false,
    future_docs: '',
    business_metrics: { users_total: 1, mrr: 0, new_mrr: 0, churn_mrr: 0, ltv: 0 },
    llm_metrics: {
      llm_cost: 0,
      roi_pct: 0,
      avg_report_cost: 0,
      contribution_margin_pct: 0,
    },
    mrr_history: [],
    ai_cost_history: [],
    tariff_kpis: [],
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
