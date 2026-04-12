import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        const status = (error as { response?: { status?: number } })?.response?.status
        if (status === 401 || status === 403 || status === 404) return false
        return failureCount < 2
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
    },
    mutations: {
      retry: false,
    },
  },
})
