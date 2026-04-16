import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { GrowthEconomicsPage } from '@/pages/GrowthEconomicsPage'

vi.mock('@/api/metrics', () => ({
  fetchMetricsOverview: vi.fn().mockResolvedValue({
    period_start: new Date().toISOString(),
    period_end: new Date().toISOString(),
    cards: [{ key: 'cr1', label: 'CR1', value: 0.2, previous_value: 0.1, delta_pct: 100, unit: 'ratio' }],
    alerts: ['CR1 below threshold'],
  }),
  fetchMetricsEconomics: vi.fn().mockResolvedValue({
    period_start: new Date().toISOString(),
    period_end: new Date().toISOString(),
    blended_cac: 1000,
    ltv_cac: 2.4,
    contribution_margin: 0.5,
    aov: 1200,
    attach_rate: 0.2,
    channel_cac: [{ channel: 'tg_ads', spend: 1000, first_paid_users: 2, cac: 500 }],
    action_hints: ['Проверить CAC'],
  }),
  fetchMetricsCohorts: vi.fn().mockResolvedValue({
    period_start: new Date().toISOString(),
    period_end: new Date().toISOString(),
    rows: [{ cohort: '2026-04', size: 10, m1: 50, m3: 30, m6: 10 }],
  }),
  fetchMarketingSpend: vi.fn().mockResolvedValue([]),
  createMarketingSpend: vi.fn(),
  fetchMetricsFunnel: vi.fn().mockResolvedValue({
    period: 'current_month',
    steps: [
      { key: 'a', title: 'Signup', count: 100, conversion_pct: 0 },
      { key: 'b', title: 'Paid', count: 50, conversion_pct: 50 },
    ],
  }),
}))

describe('GrowthEconomicsPage', () => {
  it('renders growth dashboard', async () => {
    render(<GrowthEconomicsPage />)
    await waitFor(() => expect(screen.getByText('CR1')).toBeInTheDocument())
    expect(screen.getByText('CAC by Channel')).toBeInTheDocument()
    expect(screen.getByText('Cohorts M1 / M3 / M6 (heatmap)')).toBeInTheDocument()
    expect(screen.getByText('Воронка (event-based)')).toBeInTheDocument()
  })
})
