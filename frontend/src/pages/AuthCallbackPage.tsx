import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Spin, message } from 'antd'
import { useAuthStore } from '@/stores/authStore'

export function AuthCallbackPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const setToken = useAuthStore((s) => s.setToken)

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      message.error('Токен не получен')
      navigate('/', { replace: true })
      return
    }
    setToken(token)
    message.success('Вы вошли в аккаунт')
    navigate('/dashboard', { replace: true })
  }, [params, navigate, setToken])

  return <Spin size="large" fullscreen tip="Вход…" />
}
