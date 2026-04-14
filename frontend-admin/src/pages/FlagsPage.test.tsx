import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FlagsPage } from '@/pages/FlagsPage'

vi.mock('@/api/flags', () => ({
  fetchFlags: vi.fn().mockResolvedValue([
    { key: 'admin_funnel_enabled', description: 'desc', enabled: true },
  ]),
  patchFlag: vi.fn().mockResolvedValue({ key: 'admin_funnel_enabled', description: 'desc', enabled: false }),
}))

describe('FlagsPage', () => {
  it('renders flag list', async () => {
    render(<FlagsPage />)
    await waitFor(() => {
      expect(screen.getByText('admin_funnel_enabled')).toBeInTheDocument()
    })
  })
})
