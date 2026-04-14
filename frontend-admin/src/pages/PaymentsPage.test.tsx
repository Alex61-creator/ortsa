import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PaymentsPage } from '@/pages/PaymentsPage'

vi.mock('@/api/payments', () => ({
  fetchPayments: vi.fn().mockResolvedValue([
    { order_id: 1, user_id: 2, user_email: 'u@example.com', status: 'paid', amount: '100.00', tariff_name: 'Pro', created_at: new Date().toISOString() },
  ]),
}))

describe('PaymentsPage', () => {
  it('renders and calls refresh with filters', async () => {
    render(<PaymentsPage />)
    await waitFor(() => expect(screen.getByText('u@example.com')).toBeInTheDocument())
    fireEvent.change(screen.getByPlaceholderText('ID заказа или email'), { target: { value: 'u@' } })
    fireEvent.click(screen.getByText('Обновить'))
    await waitFor(() => expect(screen.getByText('u@example.com')).toBeInTheDocument())
  })
})
