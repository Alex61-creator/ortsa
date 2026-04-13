import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Spin, message } from 'antd'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/authStore'

export function AuthCallbackPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const setToken = useAuthStore((s) => s.setToken)
  const ran = useRef(false)

  useEffect(() => {
    if (ran.current) return
    ran.current = true
    const token = params.get('token')
    if (!token) {
      message.error('Токен не получен')
      navigate('/login', { replace: true })
      return
    }
    setToken(token)

    void (async () => {
      try {
        const { data } = await api.get<{ is_admin: boolean }>('/api/v1/users/me')
        if (!data.is_admin) {
          setToken(null)
          message.warning('Доступ только для администраторов')
          navigate('/access-denied', { replace: true })
          return
        }
        message.success('Вход выполнен')
        navigate('/', { replace: true })
      } catch {
        setToken(null)
        message.error('Не удалось проверить профиль')
        navigate('/login', { replace: true })
      }
    })()
  }, [params, navigate, setToken])

  return <Spin size="large" fullscreen tip="Вход…" />
}
