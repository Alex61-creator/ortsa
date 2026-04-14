import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { TasksPage } from '@/pages/TasksPage'

vi.mock('@/api/tasks', () => ({
  fetchTasks: vi.fn().mockResolvedValue([
    { id: '1', queue: 'reports', name: 'generate_report_task', status: 'running', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  ]),
}))

describe('TasksPage', () => {
  it('renders tasks list', async () => {
    render(<TasksPage />)
    await waitFor(() => expect(screen.getByText('generate_report_task')).toBeInTheDocument())
  })
})
