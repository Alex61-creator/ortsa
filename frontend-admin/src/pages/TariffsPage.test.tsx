import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { TariffsPage } from '@/pages/TariffsPage'

vi.mock('@/api/tariffs', () => ({
  fetchTariffs: vi.fn().mockResolvedValue([
    {
      id: 1,
      code: 'report',
      name: 'Отчёт',
      price: '100.00',
      price_usd: '1.00',
      compare_price_usd: null,
      annual_total_usd: null,
      features: {},
      retention_days: 30,
      priority: 1,
      billing_type: 'one_time',
      subscription_interval: null,
      llm_tier: 'natal_full',
    },
  ]),
  patchTariff: vi.fn().mockResolvedValue({}),
}))
vi.mock('@/api/tariffHistory', () => ({
  fetchTariffHistory: vi.fn().mockResolvedValue([]),
}))

describe('TariffsPage', () => {
  it('renders tariffs table', async () => {
    render(<TariffsPage />)
    await waitFor(() => expect(screen.getByText('Отчёт')).toBeInTheDocument())
  })
})
