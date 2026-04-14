import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { UsersPage } from '@/pages/UsersPage'

vi.mock('@/api/users', () => ({
  fetchUsers: vi.fn().mockResolvedValue([
    { id: 1, email: 'user@example.com', oauth_provider: 'google', is_admin: false, created_at: new Date().toISOString(), consent_given_at: null },
  ]),
  deleteUser: vi.fn().mockResolvedValue({}),
}))
vi.mock('@/api/support', () => ({
  listUserNotes: vi.fn().mockResolvedValue([]),
  addUserNote: vi.fn().mockResolvedValue({}),
  patchUserEmail: vi.fn().mockResolvedValue({}),
  blockUser: vi.fn().mockResolvedValue({}),
  unblockUser: vi.fn().mockResolvedValue({}),
}))
vi.mock('@/api/orders', () => ({ fetchOrders: vi.fn().mockResolvedValue([]) }))

describe('UsersPage', () => {
  it('renders users table', async () => {
    render(<UsersPage />)
    await waitFor(() => expect(screen.getByText('user@example.com')).toBeInTheDocument())
  })
})
