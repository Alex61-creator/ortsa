import { Layout, Button, Space, Typography } from 'antd'
import { MoonOutlined, SunOutlined } from '@ant-design/icons'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { BackButton } from '@twa-dev/sdk/react'
import { useAuthStore } from '@/stores/authStore'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'
import { useThemeStore } from '@/stores/themeStore'
import '@/styles/global.css'

const { Header, Content, Footer } = Layout

const SPA_ENTRY_PATHS = new Set(['/order', '/order/tariff'])

export function MainLayout() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const token = useAuthStore((s) => s.token)
  const { isTwa } = useTwaEnvironment()
  const themeMode = useThemeStore((s) => s.mode)
  const setThemeMode = useThemeStore((s) => s.setMode)

  const showTwaBack = isTwa && !SPA_ENTRY_PATHS.has(location.pathname)

  return (
    <Layout className="app-root">
      {showTwaBack && <BackButton onClick={() => navigate(-1)} />}
      <Header className="app-header">
        <div className="app-header-inner">
          <Link to="/order/tariff" style={{ textDecoration: 'none' }}>
            <Typography.Title level={4} style={{ margin: 0, color: 'var(--ag-text)' }}>
              {t('appName')}
            </Typography.Title>
          </Link>
          <Space wrap>
            {!isTwa && (
              <Button
                type="text"
                aria-label={t('dashboard.toggleTheme')}
                icon={themeMode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
                onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
              />
            )}
            {token ? (
              <Link to="/dashboard">
                <Button type="primary">{t('nav.dashboard')}</Button>
              </Link>
            ) : (
              !isTwa && (
                <Button type="link" onClick={() => navigate('/order/tariff')}>
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
