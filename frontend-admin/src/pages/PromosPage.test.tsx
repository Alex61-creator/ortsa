import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PromosPage } from '@/pages/PromosPage'

vi.mock('@/api/promos', () => ({
  fetchPromos: vi.fn().mockResolvedValue([
    { id: '1', code: 'SPRING', discount_percent: 20, max_uses: 10, used_count: 1, active_until: null, is_active: true },
  ]),
  createPromo: vi.fn().mockResolvedValue({}),
  patchPromo: vi.fn().mockResolvedValue({}),
}))

describe('PromosPage', () => {
  it('renders promos list', async () => {
    render(<PromosPage />)
    await waitFor(() => expect(screen.getByText('SPRING')).toBeInTheDocument())
  })
})
