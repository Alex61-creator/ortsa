import { Layout, Button, Space, Typography } from 'antd'
import { MoonOutlined, SunOutlined } from '@ant-design/icons'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { BackButton } from '@twa-dev/sdk/react'
import { useAuthStore } from '@/stores/authStore'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'
import { useThemeStore } from '@/stores/themeStore'
import '@/styles/global.css'

const { Header, Content, Footer } = Layout

function landingOrigin(): string {
  const v = import.meta.env.VITE_LANDING_ORIGIN
  if (v && String(v).trim()) return String(v).replace(/\/$/, '')
  if (typeof window !== 'undefined') return window.location.origin
  return ''
}

const SPA_ENTRY_PATHS = new Set(['/order', '/order/tariff'])

export function MainLayout() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const token = useAuthStore((s) => s.token)
  const { isTwa } = useTwaEnvironment()
  const themeMode = useThemeStore((s) => s.mode)
  const setThemeMode = useThemeStore((s) => s.setMode)

  const siteBase = useMemo(() => landingOrigin(), [])
  const pricingHref = `${siteBase}/#pricing`

  const showTwaBack = isTwa && !SPA_ENTRY_PATHS.has(location.pathname)

  return (
    <Layout className="app-root">
      {showTwaBack && <BackButton onClick={() => navigate(-1)} />}
      <Header className="app-header">
        <div className="app-header-inner">
          <a href={siteBase} style={{ textDecoration: 'none' }}>
            <Typography.Title level={4} style={{ margin: 0, color: 'var(--ag-text)' }}>
              {t('appName')}
            </Typography.Title>
          </a>
          <Space wrap>
            {!isTwa && (
              <Button
                type="text"
                aria-label={themeMode === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
                icon={themeMode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
                onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
              />
            )}
            {token ? (
              <Link to="/dashboard/profile">
                <Button type="primary">{t('nav.dashboard')}</Button>
              </Link>
            ) : (
              !isTwa && (
                <Button href={pricingHref} type="link">
                  {t('nav.tariff')}
                </Button>
              )
            )}
          </Space>
        </div>
      </Header>
      <Content>
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <Outlet />
        </motion.div>
      </Content>
      {!isTwa && (
        <Footer className="app-footer-minimal">
          <Typography.Text type="secondary">AstroGen</Typography.Text>
        </Footer>
      )}
    </Layout>
  )
}
