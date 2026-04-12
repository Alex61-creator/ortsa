import { useEffect, useRef } from 'react'
import { Spin } from 'antd'
import { useMutation } from '@tanstack/react-query'
import { authTwa } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'

/**
 * При первом открытии Mini App обменивает initData на JWT.
 */
export function TwaAuthBootstrap() {
  const { isTwa, initData } = useTwaEnvironment()
  const token = useAuthStore((s) => s.token)
  const setToken = useAuthStore((s) => s.setToken)

  const { mutate, isPending } = useMutation({
    mutationFn: (data: string) => authTwa(data),
    onSuccess: (r) => setToken(r.access_token),
    onError: () => {
      started.current = false
    },
  })
  const started = useRef(false)

  useEffect(() => {
    if (!isTwa || !initData || token || started.current) return
    started.current = true
    mutate(initData)
  }, [isTwa, initData, token, mutate])

  if (isTwa && initData && !token && isPending) {
    return <Spin size="large" fullscreen tip="Вход через Telegram…" />
  }
  return null
}
