import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FunnelPage } from '@/pages/FunnelPage'

vi.mock('@/api/metrics', () => ({
  fetchMetricsFunnel: vi.fn().mockResolvedValue({
    period_start: new Date().toISOString(),
    period_end: new Date().toISOString(),
    steps: [{ key: 'landing', title: 'Лендинг', count: 100, conversion_pct: 100 }],
    methodology: 'event_based',
  }),
}))

describe('FunnelPage', () => {
  it('renders funnel step from api', async () => {
    render(<FunnelPage />)
    await waitFor(() => {
      expect(screen.getByText('Лендинг')).toBeInTheDocument()
    })
  })
})
