import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ActionLogPage } from '@/pages/ActionLogPage'

vi.mock('@/api/logs', () => ({
  fetchAdminLogs: vi.fn().mockResolvedValue([
    { id: '1', actor_email: 'admin@example.com', action: 'promo_patch', entity: 'promo:SPRING', created_at: new Date().toISOString() },
  ]),
}))

describe('ActionLogPage', () => {
  it('renders log rows', async () => {
    render(<ActionLogPage />)
    await waitFor(() => expect(screen.getByText('admin@example.com')).toBeInTheDocument())
  })
})
