import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FunnelPage } from '@/pages/FunnelPage'

vi.mock('@/api/funnel', () => ({
  fetchFunnelSummary: vi.fn().mockResolvedValue({
    period: 'current_month',
    steps: [{ key: 'landing', title: 'Лендинг', count: 100, conversion_pct: 100 }],
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
