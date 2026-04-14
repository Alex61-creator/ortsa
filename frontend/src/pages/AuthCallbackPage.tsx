import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Spin, message } from 'antd'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'

export function AuthCallbackPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const setToken = useAuthStore((s) => s.setToken)

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      message.error(t('auth.tokenMissing'))
      navigate('/', { replace: true })
      return
    }
    setToken(token)
    message.success(t('auth.loginSuccess'))
    navigate('/dashboard', { replace: true })
  }, [params, navigate, setToken, t])

  return <Spin size="large" fullscreen tip={t('auth.signingIn')} />
}
