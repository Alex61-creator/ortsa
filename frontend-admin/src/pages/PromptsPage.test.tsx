import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PromptsPage } from '@/pages/PromptsPage'

vi.mock('@/api/prompts', () => ({
  listPrompts: vi.fn().mockResolvedValue([
    { tariff_code: 'free', locale: 'ru', system_prompt: 'Prompt text', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'free', locale: 'en', system_prompt: 'Prompt text en', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'report', locale: 'ru', system_prompt: 'Report prompt', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'report', locale: 'en', system_prompt: 'Report prompt en', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'bundle', locale: 'ru', system_prompt: 'Bundle prompt', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'bundle', locale: 'en', system_prompt: 'Bundle prompt en', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'sub_monthly', locale: 'ru', system_prompt: 'Sub prompt', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'sub_monthly', locale: 'en', system_prompt: 'Sub prompt en', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'sub_annual', locale: 'ru', system_prompt: 'Annual prompt', is_custom: false, updated_at: null, updated_by: null },
    { tariff_code: 'sub_annual', locale: 'en', system_prompt: 'Annual prompt en', is_custom: false, updated_at: null, updated_by: null },
  ]),
  savePrompt: vi.fn().mockResolvedValue({}),
  resetPrompt: vi.fn().mockResolvedValue(undefined),
}))

describe('PromptsPage', () => {
  it('renders prompt editor', async () => {
    render(<PromptsPage />)
    await waitFor(() => expect(screen.getByDisplayValue('Prompt text')).toBeInTheDocument())
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Updated prompt' } })
    expect(screen.getByText('Сохранить')).toBeInTheDocument()
  })
})
