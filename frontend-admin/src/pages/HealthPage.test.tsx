import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { HealthPage } from '@/pages/HealthPage'

vi.mock('@/api/health', () => ({
  fetchHealthWidgets: vi.fn().mockResolvedValue([{ name: 'API', status: 'ok', value: 'online' }]),
}))

describe('HealthPage', () => {
  it('renders health cards', async () => {
    render(<HealthPage />)
    await waitFor(() => expect(screen.getByText('API')).toBeInTheDocument())
  })
})
