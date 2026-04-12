import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '@/stores/authStore'

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('sets and clears token', () => {
    useAuthStore.getState().setToken('abc')
    expect(useAuthStore.getState().token).toBe('abc')
    useAuthStore.getState().logout()
    expect(useAuthStore.getState().token).toBeNull()
  })
})
