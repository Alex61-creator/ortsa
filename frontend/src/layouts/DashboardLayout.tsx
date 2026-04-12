import { Layout, Menu, Grid, Drawer, Button } from 'antd'
import {
  UserOutlined,
  CalendarOutlined,
  ShoppingOutlined,
  MenuOutlined,
} from '@ant-design/icons'
import { useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useEffectiveThemeMode } from '@/hooks/useEffectiveThemeMode'

const { Sider, Content } = Layout

export function DashboardLayout() {
  const { t } = useTranslation()
  const colorMode = useEffectiveThemeMode()
  const location = useLocation()
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const screens = Grid.useBreakpoint()
  const [open, setOpen] = useState(false)

  const items = [
    { key: '/dashboard/profile', icon: <UserOutlined />, label: <Link to="/dashboard/profile">{t('dashboard.profile')}</Link> },
    { key: '/dashboard/natal', icon: <CalendarOutlined />, label: <Link to="/dashboard/natal">{t('dashboard.natal')}</Link> },
    { key: '/dashboard/orders', icon: <ShoppingOutlined />, label: <Link to="/dashboard/orders">{t('dashboard.orders')}</Link> },
  ]

  const selected = items.find((i) => location.pathname.startsWith(i.key))?.key ?? '/dashboard/profile'

  const menu = (
    <Menu
      theme={colorMode === 'dark' ? 'dark' : 'light'}
      mode="inline"
      selectedKeys={[selected]}
      items={items}
      onClick={() => setOpen(false)}
    />
  )

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {screens.md ? (
        <Sider breakpoint="lg" collapsedWidth={0} width={240}>
          {menu}
          <div style={{ padding: 16 }}>
            <Button
              block
              onClick={() => {
                logout()
                navigate('/')
              }}
            >
              {t('dashboard.logout')}
            </Button>
          </div>
        </Sider>
      ) : (
        <Drawer title="Menu" placement="left" onClose={() => setOpen(false)} open={open} width={260}>
          {menu}
          <Button
            block
            style={{ marginTop: 16 }}
            onClick={() => {
              logout()
              navigate('/')
            }}
          >
            {t('dashboard.logout')}
          </Button>
        </Drawer>
      )}
      <Layout>
        {!screens.md && (
          <div style={{ padding: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Button icon={<MenuOutlined />} onClick={() => setOpen(true)} />
            <span>{t('nav.dashboard')}</span>
          </div>
        )}
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
